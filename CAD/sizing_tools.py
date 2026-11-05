"""Example of Python tools for one persistent circuit-sizing experiment.

Copy this file and mcp_server.py to your CAD project root.
"""

import os
from copy import deepcopy
from datetime import datetime
from numbers import Real
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

os.environ.setdefault("MPLBACKEND", "Agg")
from circuit_env import CircuitEnv
from td3 import ReplayBuffer, TD3


SPEC_UNITS = {
    "area": "m^2", "current": "A", "gain": "V/V", "noise": "V RMS",
    "phm": "deg", "slewRate": "V/us", "ugbw": "Hz",
}
MAX_STEPS_PER_CALL = 1000


def to_builtin(value):
    """Convert NumPy values to JSON-compatible Python values."""
    if isinstance(value, np.ndarray):
        return to_builtin(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {key: to_builtin(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_builtin(item) for item in value]
    return value


def check_count(value, name, maximum):
    """Reject booleans, non-integers, and out-of-range requests."""
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be an integer from 1 to {maximum}.")


class SizingExperiment:
    """One agent, replay buffer, and episode shared by successive tool calls.

    State lives in this object until the Python process exits. Use one experiment
    per process: the existing TD3 code uses NumPy/PyTorch global random generators.
    """

    def __init__(self, seed=123456, batch_size=100, replay_size=100_000):
        check_count(replay_size, "replay_size", 1_000_000)
        check_count(batch_size, "batch_size", replay_size)
        if type(seed) is not int or not 0 <= seed < 2**32:
            raise ValueError("seed must be an integer from 0 to 2**32 - 1.")
        np.random.seed(seed)
        torch.manual_seed(seed)
        self.seed = seed
        self.batch_size = batch_size
        self.run_id = "mcp_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        self.env = CircuitEnv(run_id=self.run_id, success_threshold=0.0)
        # Direct design evaluations must not change the ongoing RL episode.
        self.evaluation_env = CircuitEnv(run_id=self.run_id + "_evaluate",
                                         success_threshold=0.0)
        self.env.action_space.seed(seed)
        Path(self.env.simulation_engine.output_files_folder).mkdir(parents=True, exist_ok=True)
        Path("solutions").mkdir(exist_ok=True)

        args = SimpleNamespace(gamma=0.99, tau=0.005, noise_sigma=0.1,
                               actor_update_interval=2, pi_lr=3e-4, q_lr=3e-4,
                               hidden_size=256, cuda=False)
        self.agent = TD3(self.env.observation_space.shape[0], self.env.action_space, args)
        self.replay = ReplayBuffer(self.env.observation_space.shape[0],
                                   self.env.action_space.shape[0], max_size=replay_size)
        self.observation = None  # None means the next RL step needs a reset.
        self.warmup_steps = 0
        self.training_steps = 0
        self.updates = 0
        self.simulator_calls = 0  # Attempts, including resets and failed calls.
        self.candidates = {}  # Parameter tuple -> latest measured result.

    def simulate(self, parameters: dict[str, float]) -> dict:
        """Evaluate one complete physical-parameter dictionary on the YAML grid.

        Return parameters, specs, normalized_specs, reward, constraint satisfaction,
        source, and spec_units. Record the candidate, without changing RL state,
        replay, or weights. Validation failures do not invoke the simulator.
        """
        # invalid designs raise an error here, before any simulator call is used
        clean_parameters = self._validate_parameters(parameters)

        # evaluation_env is a separate environment, so the RL episode is not touched
        self.simulator_calls += 1
        specs = self.evaluation_env.simulate(clean_parameters)

        candidate = self._record(self.evaluation_env, clean_parameters, specs, "simulate")

        # give the caller a copy, so changing it cannot change the stored history
        result = deepcopy(candidate)
        result["spec_units"] = dict(SPEC_UNITS)
        return result

    def warmup(self, n_steps: int) -> dict:
        """Append exactly n_steps random transitions, without updating weights.

        Continue the current episode. Return cumulative status plus steps_completed,
        experiences_added, simulator_calls_used, and updates_performed for this call.
        n_steps must be 1..1000. Reset simulations count as calls, not transitions.
        """
        return self._run_steps(n_steps, training=False)

    def train(self, n_steps: int) -> dict:
        """Collect exactly n_steps policy transitions and perform TD3 updates.

        Require at least batch_size experiences before starting. Reuse the same
        agent, replay, and unfinished episode. One learning update per new
        transition; the agent controls delayed actor updates. Return the same
        status and per-call counts as warmup. n_steps must be 1..1000.
        """
        # the agent learns from a random batch, so the buffer must hold enough first
        if self.replay.size < self.batch_size:
            raise RuntimeError(f"Training needs at least {self.batch_size} experiences, "
                               f"but the replay buffer has {self.replay.size}. Run warmup first.")

        return self._run_steps(n_steps, training=True)

    def get_status(self, k: int = 5) -> dict:
        """Return progress and the top k distinct measured designs (k=1..20).

        Rank by reward, highest first; a high reward does not imply feasibility.
        Include reset and standalone evaluations in candidate history. This call
        performs no simulations, sampling, or learning, and returns detached data.
        """
        check_count(k, "k", 20)

        # sort all stored designs by reward, highest first
        ranked_candidates = sorted(self.candidates.values(),
                                   key=lambda candidate: candidate["reward"],
                                   reverse=True)

        status = {
            "seed": self.seed,
            "batch_size": self.batch_size,
            "warmup_steps": self.warmup_steps,
            "training_steps": self.training_steps,
            "updates": self.updates,
            "simulator_calls": self.simulator_calls,
            "replay_size": self.replay.size,
            "episode_in_progress": self.observation is not None,
            "distinct_candidates": len(self.candidates),
            # a copy, so changing the returned data cannot change the stored history
            "best_candidates": deepcopy(ranked_candidates[:k]),
        }
        return to_builtin(status)

    def _validate_parameters(self, parameters):
        """Require every YAML parameter, finite numbers, and valid grid values.

        Use the same np.arange(min, max, step) grids as phase one. Canonicalize
        floating-point roundoff only; reject off-grid values rather than clipping.
        """
        # missing parameters -> parameters in yaml but not in the input dictionary from LLM
        # extra parameters -> parameters in the input dictionary from LLM but not in the yaml
        ranges = self.env.param_ranges
        missing_parameters = set(ranges) - set(parameters)
        extra_parameters = set(parameters) - set(ranges)
        if missing_parameters or extra_parameters:
            raise ValueError(f"Missing parameters: {missing_parameters}, Extra unknown parameters: {extra_parameters}")

        clean_parameters = {}

        # check that every value is a usable number on the yaml grid
        for name in ranges:
            value = parameters[name]

            # True and False count as numbers in Python, so reject them first
            if isinstance(value, bool):
                raise ValueError(f"{name} must be a number, but got {value!r}")

            # this check must come before np.isfinite, which crashes on text
            if not isinstance(value, Real):
                raise ValueError(f"{name} must be a number, but got {value!r}")

            # nan and inf are not usable values for a circuit parameter
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite, but got {value!r}")

            # same grid as action_refine in circuit_env.py (max is not included)
            p_min = float(ranges[name]['min'])
            p_max = float(ranges[name]['max'])
            p_step = float(ranges[name]['step'])
            grid = np.arange(p_min, p_max, p_step)

            # find the grid point closest to the value
            closest_index = np.argmin(np.abs(grid - value))
            closest_value = float(grid[closest_index])

            # allow only tiny roundoff errors, measured relative to the step size
            if abs(closest_value - value) > 1e-6 * p_step:
                raise ValueError(f"{name}={value!r} is not on the grid: min {p_min}, "
                                 f"last valid value {float(grid[-1])}, step {p_step}")

            # m and res have whole-number grids, so store them as int like action_refine
            if p_min.is_integer() and p_max.is_integer() and p_step.is_integer():
                closest_value = int(round(closest_value))

            clean_parameters[name] = closest_value

        return clean_parameters

    def _record(self, env, parameters, specs, source):
        """Validate and save one candidate using the environment's scoring methods.

        Return a JSON-compatible candidate. Repeated parameters replace their
        previous measurement; failed or non-finite results must not enter history.
        """
        # every spec must be a finite number
        for spec_name, spec_value in specs.items():
            if not np.isfinite(spec_value):
                raise RuntimeError(f"Simulation failed: {spec_name} is {spec_value}.")

        # a failed simulation does not return nan: circuit_env.py simulate() returns
        # these exact finite values instead, so they must be checked for separately
        targets = env.dict_targets
        simulation_failed = (specs["gain"] == 0.0
                             and specs["ugbw"] == 0.0
                             and specs["phm"] == 0.0
                             and specs["slewRate"] == 0.0
                             and specs["noise"] == targets["noise"] * 1000
                             and specs["current"] == targets["current"] * 1000
                             and specs["area"] == targets["area"] * 1000)
        if simulation_failed:
            raise RuntimeError("Simulation failed: ngspice or the measurements gave no valid result.")

        # score the design with the same methods the RL environment uses
        normalized_specs = env.normalize_specs(specs)
        reward, hard_satisfied = env.reward_computation(normalized_specs)

        # to_builtin turns NumPy values into plain Python values for JSON
        candidate = to_builtin({
            "parameters": dict(parameters),
            "specs": dict(specs),
            "normalized_specs": normalized_specs,
            "reward": reward,
            "hard_constraints_satisfied": hard_satisfied,
            "source": source,
        })

        # a tuple can be a dictionary key, and a repeated design replaces its old entry
        design_key = tuple(candidate["parameters"][name] for name in env.param_ranges)
        self.candidates[design_key] = candidate
        return candidate

    def _run_steps(self, n_steps, training):
        """Run a bounded batch, preserving episode state and reporting partial failures.

        Return get_status() plus per-call counts. Store full replay transitions;
        failed evaluations must not enter replay. Keep already completed work if
        a later step fails, and tell the caller to inspect get_status() before retrying.
        """
        check_count(n_steps, "n_steps", MAX_STEPS_PER_CALL)

        # remember the counters, to report what this one call added
        calls_before = self.simulator_calls
        updates_before = self.updates
        steps_completed = 0

        if training:
            source = "train"
        else:
            source = "warmup"

        try:
            while steps_completed < n_steps:
                # no episode is running, so start one (this costs one simulation)
                if self.observation is None:
                    self.simulator_calls += 1
                    observation = self.env.reset()
                    self._record(self.env, self.env.param_values, self.env.real_specs, "reset")
                    self.observation = observation

                # the policy chooses during training, random actions during warmup
                if training:
                    action = self.agent.select_action(self.observation)
                else:
                    action = self.env.action_space.sample()

                self.simulator_calls += 1
                next_observation, reward, done, info = self.env.step(action)

                # _record raises an error on a failed simulation, so push is skipped
                self._record(self.env, self.env.param_values, self.env.real_specs, source)
                self.replay.push(self.observation, action, reward, next_observation, done)
                steps_completed += 1

                if training:
                    self.training_steps += 1
                else:
                    self.warmup_steps += 1

                # None means the next step starts a new episode
                if done:
                    self.observation = None
                else:
                    self.observation = next_observation

                # one learning update per new transition, same order as td3_runner.py
                if training:
                    batch = self.replay.sample(self.batch_size)
                    self.agent.update_parameters(memory_batch=batch, update=self.updates)
                    self.updates += 1

                # clean up the no_backup folder every 100 steps, like td3_runner.py
                if (self.warmup_steps + self.training_steps) % 100 == 0:
                    os.system('./clean.sh')

        except Exception as error:
            # finished steps stay in replay; a new episode starts on the next call
            self.observation = None
            raise RuntimeError(f"Stopped after {steps_completed} of {n_steps} steps: {error} "
                               "Completed work is kept. Call get_status before retrying.") from error

        result = self.get_status()
        result["steps_completed"] = steps_completed
        result["experiences_added"] = steps_completed
        result["simulator_calls_used"] = self.simulator_calls - calls_before
        result["updates_performed"] = self.updates - updates_before
        return result
