
import pytest
import numpy as np
from unittest.mock import MagicMock

from circuit_env import CircuitEnv


# -----------------------------------------
# TEST 1: action_refine()
# -----------------------------------------

def test_action_refine():
    # 1. Create CircuitEnv without running its constructor
    env = CircuitEnv.__new__(CircuitEnv)

     # 2. Define the parameter range (normally obtained from YAML)
    env.param_ranges = {
    'W1': {'min': 1, 'max': 10, 'step': 2}
    }

     # 3. Give the agent's normalized action
    action = [0.8]

    # 4. Execute the function we want to test
    actual_action = env.action_refine(action)

    # 5. Define the expected result
    expected_action = {'W1': 7}

    # 6. Compare actual output with expected output
    assert actual_action == expected_action

# -----------------------------------------
# TEST 2: simulate()
# -----------------------------------------

def test_simulate_success():
    env = CircuitEnv.__new__(CircuitEnv)
    env.counter = 0

    env.pvt_corner = {
        'process': 'TT',
        'temp': 27,
        'voltage': 1.2
    }
    
    env.simulation_engine = MagicMock()
    env.simulation_engine.create_new_netlist.return_value = "mock_netlist.sp"
    env.simulation_engine.simulate.return_value = 0

    measured_spec = {
    'gain': 250.0,
    'ugbw': 15.0,
    'phm': 60.0,
    'slewRate': 12.0,
    'noise': 8.0,
    'current': 120.0,
    'area': 45.0
    }

    env.simulation_engine.measure_metrics.return_value = measured_spec

    params = {
    'W1': 7,
    'L1': 2,
    'W2': 5
    }

    actual_result = env.simulate(params)

    assert env.counter == 1

    env.simulation_engine.create_new_netlist.assert_called_once_with(
    params,
    process='TT',
    temp_pvt=27,
    vdd=1.2
    )

    env.simulation_engine.simulate.assert_called_once_with(
    "mock_netlist.sp"
    )

    env.simulation_engine.measure_metrics.assert_called_once()

    assert actual_result == measured_spec

