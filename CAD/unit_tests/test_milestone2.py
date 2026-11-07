import csv
import os
import numpy as np
import pytest
from circuit_env import CircuitEnv

@pytest.fixture(scope="module")
def env():
    os.makedirs("unit_tests/solutions", exist_ok=True)
    if os.path.exists("unit_tests/solutions/unit_test_m2.csv"):
        os.remove("unit_tests/solutions/unit_test_m2.csv")
    return CircuitEnv(run_id="../unit_tests/solutions/unit_test_m2")

def test_action_lowest(env):
    action = np.full(env.n_actions, -1.0)
    params = env.action_refine(action)
    assert params['mp1'] == 1
    assert params['wp1'] == pytest.approx(0.25e-6)
    assert params['lp1'] == pytest.approx(45e-9)
    assert params['cap'] == pytest.approx(0.1e-12, abs=1e-15)
    assert params['res'] == 0
    
def test_action_middle(env):
    action = np.full(env.n_actions, 0.0)
    params = env.action_refine(action)
    assert params['mp1'] == 12
    assert params['wp1'] == pytest.approx(1.5e-6)
    assert params['lp1'] == pytest.approx(90e-9)
    assert params['cap'] == pytest.approx(5e-12, abs=1e-15)
    assert params['res'] == 4900

def test_action_highest(env):
    action = np.full(env.n_actions, 1.0)
    params = env.action_refine(action)
    assert params['mp1'] == 24
    assert params['wp1'] == pytest.approx(2.75e-6)
    assert params['lp1'] == pytest.approx(180e-9)
    assert params['cap'] == pytest.approx(9.9e-12, abs=1e-15)
    assert params['res'] == 9800

def test_action_clipping(env):
    too_big = np.full(env.n_actions, 2.0)
    too_small = np.full(env.n_actions, -2.0)
    assert env.action_refine(too_big) == env.action_refine(np.full(env.n_actions, 1.0))
    assert env.action_refine(too_small) == env.action_refine(np.full(env.n_actions, -1.0))

hand_specs = {'area': 1e-9, 'current': 1e-4, 'gain': 300, 'noise': 0.01,
              'phm': 180, 'slewRate': 90, 'ugbw': 300e6}

hand_norms = {'area': -1/3, 'current': -1/3, 'gain': 0.2, 'noise': -0.5,
              'phm': 0.5, 'slewRate': 0.5, 'ugbw': 0.5}

def test_normalize_specs(env):
    norms = env.normalize_specs(hand_specs)
    for name in hand_norms:
        assert norms[name] == pytest.approx(hand_norms[name], rel=1e-6)

def test_reset(env):
    env.episode_steps = 7
    env.score = 5.0
    ob = env.reset(seed=0)
    assert env.episode_steps == 0
    assert env.score == 0
    assert len(ob) == 7
    assert ob.dtype == np.float32

def test_step_one(env):
    env.reset(seed=0)
    action = np.full(env.n_actions, 0.0)
    ob, reward, done, info = env.step(action)
    expected_reward, expected_hard = env.reward_computation(env.cur_norm_specs)
    assert env.param_values['mp1'] == 12
    assert len(ob) == 7
    assert reward == expected_reward
    assert info['hard_satisfied'] == expected_hard
    assert done == False
    assert env.episode_steps == 1

def test_step_done_after_10(env):
    env.reset(seed=0)
    action = np.full(env.n_actions, 0.0)
    for i in range(9):
        ob, reward, done, info = env.step(action)
        assert done == False
    ob, reward, done, info = env.step(action)
    assert done == True

def test_negative_phase_margin(env):
    specs = dict(hand_specs)
    specs['phm'] = -20
    norms = env.normalize_specs(specs)
    assert norms['phm'] == pytest.approx(-1.0, rel=1e-6)

def test_reward_hard_violated(env):
    norms = {'area': -0.2, 'current': 0.4, 'gain': -0.5, 'noise': 0.1,
             'phm': 0.1, 'slewRate': 0.2, 'ugbw': 0.3}
    reward, hard_satisfied = env.reward_computation(norms)
    assert reward == pytest.approx(-0.61, rel=1e-6)
    assert hard_satisfied == False

def test_reward_all_met(env):
    norms = {'area': -0.2, 'current': -0.4, 'gain': 0.1, 'noise': -0.3,
             'phm': 0.1, 'slewRate': 0.2, 'ugbw': 0.3}
    reward, hard_satisfied = env.reward_computation(norms)
    assert reward == pytest.approx(0.9, rel=1e-6)
    assert hard_satisfied == True

def load_reference_data():
    # Load reference data from references.csv
    path = os.path.join(os.getcwd(), "unit_tests", "references.csv")
    with open(path, newline="") as f:
         rows = list(csv.DictReader(f))
    ref_designs = {}
    for i in ["Design 1", "Design 2", "Design 3", "Design 4", "Design 5"]:
        ref_designs[i] = {}
        for row in rows:
            ref_designs[i][row["Attribute"]] = float(row[i])
    return ref_designs

references = load_reference_data()
@pytest.mark.parametrize("ref_design", references.keys())
def test_reference_designs_action(env, ref_design):
    ref = references[ref_design]  
    action = []
    for name in env.param_ranges:
        action.append(ref["action_" + name])
    params = env.action_refine(action)
    for name in env.param_ranges:
        assert params[name] == pytest.approx(ref["param_" + name], rel=1e-6, abs=0) 

@pytest.mark.parametrize("ref_design", references.keys())
def test_ref_normalize_specs(env, ref_design):
    ref = references[ref_design]
    specs = {}
    for name in env.dict_targets:
        specs[name] = ref["spec_" + name]
    norms = env.normalize_specs(specs)
    for name in env.dict_targets:
        assert norms[name] == pytest.approx(ref["norm_" + name], rel=1e-6)

@pytest.mark.parametrize("ref_design", references.keys())
def test_ref_reward(env, ref_design):
    ref = references[ref_design]
    norms = {}
    for name in env.dict_targets:
        norms[name] = ref["norm_" + name]
    reward, hard_satisfied = env.reward_computation(norms)
    assert reward == pytest.approx(ref["reward"], rel=1e-6)
    assert hard_satisfied == False

TwoStage_cir_params = {'mp1': 10, 'wp1': 0.5e-6, 'lp1': 90e-9,
                       'mn1': 38, 'wn1': 0.5e-6, 'ln1': 90e-9,
                       'mp3': 4,  'wp3': 0.5e-6, 'lp3': 90e-9,
                       'mn3': 9,  'wn3': 0.5e-6, 'ln3': 90e-9,
                       'mn4': 20, 'wn4': 0.5e-6, 'ln4': 90e-9,
                       'mn5': 60, 'wn5': 0.5e-6, 'ln5': 90e-9,
                       'cap': 3e-12, 'res': 1000}
def read_netlist_params(path):
    values = {}
    with open(path) as f:
        for line in f:
            if line.startswith(".param"):
                for word in line.split():
                    if "=" in word:
                        name, value = word.split("=")
                        values[name] = value
    return values

def test_simulate_writes_netlist(env):
    env.simulate(TwoStage_cir_params)
    engine = env.simulation_engine
    path = os.path.join(engine.output_netlists_folder, engine.random_name + ".cir")
    netlist = read_netlist_params(path)
    for name in TwoStage_cir_params:
        assert float(netlist[name]) == pytest.approx(TwoStage_cir_params[name], rel=1e-6, abs=0)
    assert float(netlist['VDD']) == 1.2
    assert float(netlist['temp_pvt']) == 27

def test_simulate_failed(env, monkeypatch):
    def fake_simulate(netlist_path):
        return 1
    monkeypatch.setattr(env.simulation_engine, "simulate", fake_simulate)
    specs = env.simulate(TwoStage_cir_params)
    assert specs['gain'] == 0
    assert specs['ugbw'] == 0
    assert specs['phm'] == 0
    assert specs['slewRate'] == 0
    assert specs['noise'] == pytest.approx(30)
    assert specs['current'] == pytest.approx(0.2)
    assert specs['area'] == pytest.approx(2e-6)

def test_simulate_nan_measurement(env, monkeypatch):
    def fake_measure():
        return {'area': 1e-9, 'current': 1e-4, 'gain': float('nan'), 'noise': 0.01,
                'phm': 70, 'slewRate': 40, 'ugbw': 2e8}
    monkeypatch.setattr(env.simulation_engine, "measure_metrics", fake_measure)
    specs = env.simulate(TwoStage_cir_params)
    assert specs['gain'] == 0
    assert specs['noise'] == pytest.approx(30)

@pytest.mark.parametrize("ref_design", references.keys())
def test_ref_netlist(env, ref_design):
    ref = references[ref_design]
    action = []
    for name in env.param_ranges:
        action.append(ref["action_" + name])
    params = env.action_refine(action)
    env.simulate(params)
    engine = env.simulation_engine
    path = os.path.join(engine.output_netlists_folder, engine.random_name + ".cir")
    netlist = read_netlist_params(path)
    for name in env.param_ranges:
        assert float(netlist[name]) == pytest.approx(ref["param_" + name], rel=1e-6, abs=0)

@pytest.mark.parametrize("ref_design", references.keys())
def test_ref_step(env, ref_design):
    ref = references[ref_design]
    action = []
    for name in env.param_ranges:
        action.append(ref["action_" + name])
    env.reset(seed=0)
    ob, reward, done, info = env.step(action)
    for name in env.dict_targets:
        assert env.real_specs[name] == pytest.approx(ref["spec_" + name], rel=0.05)
    assert reward == pytest.approx(ref["reward"], abs=0.02)
    assert info['hard_satisfied'] == False
