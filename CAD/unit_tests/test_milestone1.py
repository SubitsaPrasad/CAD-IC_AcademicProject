import os
import numpy as np
import pytest
from ngspice_interface.dut_testbench import DUT

@pytest.fixture(scope="module")
def dut():
    yaml_path = os.path.join(os.getcwd(), "ngspice_interface", "files", "yaml_files", "TwoStage.yaml")
    return DUT(yaml_path)

@pytest.fixture(scope="module")
def ac_data():
    raw = np.genfromtxt(os.path.join(os.getcwd(), "output", "ac_TwoStage.csv"), skip_header=1)
    freq = raw[:, 0]
    vout = raw[:, 1] + 1j * raw[:, 2]
    return freq, vout

def test_dc_gain(dut):
    vout = np.array([1.1778811e+00-1.3310285e-06j, 3.0573730e-05-2.8186610e-05j])
    gain = dut.find_dc_gain(vout)
    assert gain == pytest.approx(1.1778811)

def test_ugbw(dut, ac_data):
    freq, vout = ac_data
    #values from meas and plot in ngspice
    assert dut.find_ugbw(freq, vout) == pytest.approx(605895, rel=0.01)

def test_phm(dut, ac_data):
    freq, vout = ac_data
    assert dut.find_phm(freq, vout) == pytest.approx(144.63, rel=0.01)

def test_slew_rate(dut):
    raw = np.genfromtxt(os.path.join(os.getcwd(), "unit_tests", "tran_TwoStage.csv"), skip_header=1)
    time, vout = raw[:, 0], raw[:, 1]
    assert dut.find_slew_rate(time, vout) == pytest.approx(3.7641, rel=0.01)

def test_flat_gain(dut):
    f = np.logspace(0, 10, 2001)
    vout = 1000 * np.ones_like(f) + 0j
    assert dut.find_ugbw(f, vout) == 0.0
    assert dut.find_phm(f, vout) == 0.0

def test_flat_signal(dut):
    t = np.linspace(0, 3e-6, 3001)
    signal = np.full_like(t, 0.6)
    assert dut.find_slew_rate(t, signal) == 0.0

def test_ngspice_fail(dut):
    dut.random_name = "does_not_exist"
    with pytest.raises(FileNotFoundError):
        dut.measure_metrics()

ref_designs = {}

ref_designs[0] = {
    "parameters": {
        'mp1': 6,  'wp1': 2.25e-06, 'lp1': 1.35e-07,
        'mn1': 10, 'wn1': 5e-07,   'ln1': 1.35e-07,
        'mp3': 10, 'wp3': 1.75e-06, 'lp3': 9e-08,
        'mn3': 1,  'wn3': 1e-06,   'ln3': 1.35e-07,
        'mn4': 9,  'wn4': 1.25e-06, 'ln4': 1.35e-07,
        'mn5': 6,  'wn5': 7.5e-07, 'ln5': 9e-08,
        'cap': 8e-13, 'res': 9500.0
    },
    "specifications": {
        'area': 9.77377845238e-10,
        'current': 0.00050714721,
        'gain': 817.232450005,
        'noise': 0.039446578,
        'phm': 47.8961300513,
        'slewRate': 72.1326503247,
        'ugbw': 287939270.262,
    }
}

ref_designs[1] = {
    "parameters": {
        'mp1': 15, 'wp1': 1.25e-06, 'lp1': 9e-08,
        'mn1': 10, 'wn1': 1e-06,   'ln1': 9e-08,
        'mp3': 12, 'wp3': 1.25e-06, 'lp3': 9e-08,
        'mn3': 15, 'wn3': 1.5e-06,  'ln3': 9e-08,
        'mn4': 11, 'wn4': 1.5e-06,  'ln4': 9e-08,
        'mn5': 11, 'wn5': 1e-06,   'ln5': 9e-08,
        'cap': 4.5e-12, 'res': 4800.0
    },
    "specifications": {
        'area': 1.89397314286e-09,
        'current': 6.3062567e-05,
        'gain': 89.63791,
        'noise': 0.0028557284,
        'phm': 52.44050,
        'slewRate': 4.939156,
        'ugbw': 4172794.0,
    }
}

ref_designs[2] = {
    "parameters": {
        'mp1': 7,  'wp1': 1.75e-06, 'lp1': 1.35e-07,
        'mn1': 20, 'wn1': 2.25e-06, 'ln1': 1.35e-07,
        'mp3': 22, 'wp3': 2.25e-06, 'lp3': 1.35e-07,
        'mn3': 21, 'wn3': 1e-06,   'ln3': 9e-08,
        'mn4': 8,  'wn4': 7.5e-07, 'ln4': 9e-08,
        'mn5': 17, 'wn5': 2.5e-07, 'ln5': 4.5e-08,
        'cap': 8e-13, 'res': 3900.0
    },
    "specifications": {
        'area': 6.33842845238e-10,
        'current': 5.8465647e-05,
        'gain': 151.1024,
        'noise': 0.0023655671,
        'phm': 44.35755,
        'slewRate': 9.157325,
        'ugbw': 8581284.0,
    }
}

ref_designs[3] = {
    "parameters": {
        'mp1': 8,  'wp1': 1.5e-06,  'lp1': 1.35e-07,
        'mn1': 15, 'wn1': 1.75e-06, 'ln1': 1.35e-07,
        'mp3': 18, 'wp3': 2e-06,    'lp3': 1.35e-07,
        'mn3': 15, 'wn3': 1.25e-06, 'ln3': 9e-08,
        'mn4': 13, 'wn4': 1.5e-06,  'ln4': 9e-08,
        'mn5': 17, 'wn5': 5e-07,    'ln5': 4.5e-08,
        'cap': 3.5e-12, 'res': 6000.0
    },
    "specifications": {
        'area': 1.66640309524e-09,
        'current': 0.00011065298,
        'gain': 188.3551,
        'noise': 0.0030385342,
        'phm': 103.4538,
        'slewRate': 6.894445,
        'ugbw': 14700610.0,
    }
}

ref_designs[4] = {
    "parameters": {
        'mp1': 12, 'wp1': 7.5e-07,  'lp1': 1.35e-07,
        'mn1': 15, 'wn1': 1.5e-06,  'ln1': 1.35e-07,
        'mp3': 10, 'wp3': 1.5e-06,  'lp3': 9e-08,
        'mn3': 19, 'wn3': 1.75e-06, 'ln3': 9e-08,
        'mn4': 13, 'wn4': 1.25e-06, 'ln4': 9e-08,
        'mn5': 13, 'wn5': 1e-06,   'ln5': 4.5e-08,
        'cap': 2.4e-12, 'res': 7500.0
    },
    "specifications": {
        'area': 1.39673478571e-09,
        'current': 7.4730221e-05,
        'gain': 54.21959,
        'noise': 0.00101217,
        'phm': 96.87317,
        'slewRate': 4.49630541577,
        'ugbw': 4747450.57736,
    }
}

# 5% tolerance TA criterion
REL_TOL = 0.05 
SPECS = ["area", "current", "gain", "noise", "phm", "slewRate", "ugbw"]

@pytest.fixture(scope="module")
def measured():
    yaml_path = os.path.join(os.getcwd(), "ngspice_interface", "files", "yaml_files", "TwoStage.yaml")
    results = {}
    for i, design in ref_designs.items():
        dut = DUT(yaml_path)
        netlist_path = dut.create_new_netlist(design["parameters"], process='TT', temp_pvt = 27, vdd = 1.2)
        info = dut.simulate(netlist_path)
        assert info == 0
        results[i] = dut.measure_metrics()
        print(i, results[i])
    return results 


@pytest.mark.parametrize("design", ref_designs.keys())
@pytest.mark.parametrize("spec", SPECS)
def test_spec_matches_reference(measured, design, spec):
    reference = ref_designs[design]["specifications"][spec]
    assert measured[design][spec] == pytest.approx(reference, rel=REL_TOL)

