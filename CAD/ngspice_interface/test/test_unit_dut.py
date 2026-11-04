
import pytest
import numpy as np

from ngspice_interface.dut_testbench import DUT


# -----------------------------------------
# TEST 1: DC GAIN
# -----------------------------------------

def test_find_dc_gain():

    dut = DUT.__new__(DUT)   # Creation of object without initialization

    vout = np.array([
        100 + 0j,
        50 + 0j,
        10 + 0j
    ])

    result = dut.find_dc_gain(vout)

    assert result == pytest.approx(100.0)


# -----------------------------------------
# TEST 2: UNITY GAIN BANDWIDTH
# -----------------------------------------

def test_find_ugbw():

    dut = DUT.__new__(DUT)

    freq = np.array([1, 10, 100])

    vout = np.array([
        10 + 0j,
        1 + 0j,
        0.1 + 0j
    ])

    result = dut.find_ugbw(freq, vout)

    assert result == pytest.approx(10.0)


# -----------------------------------------
# TEST 3: PHASE MARGIN
# -----------------------------------------

def test_find_phm():

    dut = DUT.__new__(DUT)

    freq = np.array([1, 10, 100])

    magnitude = np.array([10, 1, 0.1])

    phase = np.array([-90, -135, -180])

    vout = magnitude * np.exp(1j * np.deg2rad(phase))

    result = dut.find_phm(freq, vout)

    assert result == pytest.approx(45.0)


# -----------------------------------------
# TEST 4: SLEW RATE
# -----------------------------------------

def test_find_slew_rate():

    dut = DUT.__new__(DUT)

    time = np.array([
        0, 1e-6, 2e-6, 3e-6, 4e-6
    ])

    signal = np.array([
        0, 1, 1, 0, 0
    ])

    result = dut.find_slew_rate(
        time,
        signal,
        threshold_low=0.1,
        threshold_high=0.9,
        time_unit='us'
    )

    assert result == pytest.approx(1.0)


# -----------------------------------------
# TEST 5: BEST CROSSING
# -----------------------------------------

def test_get_best_crossing():

    dut = DUT.__new__(DUT)

    xvec = np.array([0, 1, 2])

    yvec = np.array([-1, 0, 1])

    val = 0

    result, success = dut._get_best_crossing(
        xvec,
        yvec,
        val
    )

    assert result == pytest.approx(1.0)
    assert success is True


# -----------------------------------------
# TEST 6: NO CROSSING
# -----------------------------------------

def test_get_best_crossing_no_crossing():

    dut = DUT.__new__(DUT)

    xvec = np.array([0, 1, 2])

    yvec = np.array([1, 2, 3])

    val = 0

    result, success = dut._get_best_crossing(
        xvec,
        yvec,
        val
    )

    assert result == pytest.approx(2.0)
    assert success is False
