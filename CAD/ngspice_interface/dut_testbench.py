import time
import numpy as np
import os
import scipy.interpolate as interp
import scipy.optimize as sciopt
from scipy.optimize import differential_evolution
from .area_estimation import BPTM45nmAreaEstimator
from .ngspice_wrapper import NgspiceWrapper


class DUT(NgspiceWrapper):

    def evaluate_circuit(self, parameters):

        # 1. Generate netlist
        netlist_path = self.create_new_netlist(parameters)

        # 2. Run Ngspice
        status = self.simulate(netlist_path)

        # 3. Read CSV files
        self.parse_outputs()

        # 4. Calculate performance metrics
        metrics = self.measure_metrics()

        # 5. Return results
        return metrics

    
    def measure_metrics(self):
        self.parse_outputs()
        spec_dict = {}
        # post process raw data
        area_estimator = BPTM45nmAreaEstimator(self.circuit_params, self.circuit_multipliers)
        spec_dict['area'] = area_estimator.find_area()
        spec_dict['current'] = self.current
        spec_dict['gain'] = self.find_dc_gain(self.vout_complex)
        spec_dict['noise'] = self.noise
        spec_dict['phm'] = self.find_phm(self.freq, self.vout_complex)
        spec_dict['slewRate'] = self.find_slew_rate(self.time, self.vout_tran, threshold_low=0.1, threshold_high=0.9, time_unit='us')
        spec_dict['ugbw'] = self.find_ugbw(self.freq, self.vout_complex)

        return spec_dict
    
    def parse_outputs(self):
        tran_fname = os.path.join(self.output_files_folder, 'tran_'+self.random_name+'.csv')
        ac_fname = os.path.join(self.output_files_folder, 'ac_'+self.random_name+'.csv')
        dc_fname = os.path.join(self.output_files_folder, 'dc_'+self.random_name+'.csv')
        noise_fname = os.path.join(self.output_files_folder, 'noise_'+self.random_name+'.csv')
        # add these file names in a list
        self.output_files = [tran_fname, ac_fname, dc_fname, noise_fname]
        for file in self.output_files:
            if not os.path.isfile(file):
                print(f"{file} doesn't exist")
        tran_raw_outputs = np.genfromtxt(tran_fname, skip_header=1)
        ac_raw_outputs = np.genfromtxt(ac_fname, skip_header=1)
        dc_raw_outputs = np.genfromtxt(dc_fname, skip_header=1)
        noise_raw_outputs = np.genfromtxt(noise_fname, skip_header=1)

        self.time = tran_raw_outputs[:, 0]
        self.vout_tran = tran_raw_outputs[:, 1]
        
        self.freq = ac_raw_outputs[:, 0]
        vout_real = ac_raw_outputs[:, 1]
        vout_imag = ac_raw_outputs[:, 2]
        self.vout_complex = vout_real + 1j*vout_imag
        
        self.current = - dc_raw_outputs[1]

        self.noise = noise_raw_outputs[0]
    
    def find_dc_gain(self, vout):
        """
        TODO: Implement the DC gain calculation
        
        Hint:
        Use numpy's abs() function to calculate the magnitude of the complex number at each point.
        """
        return np.abs(vout[0])
        
    def find_ugbw(self, freq, vout):
        """
        TODO: Implement the unity gain bandwidth (UGBW) calculation
        """
        v1 = np.abs(vout)
        if np.any(freq <= 0) or np.any(v1 <= 0):
            return 0.0
        freq_log = np.log10(freq)
        gain_log = np.log10(v1)
        ugbw_log, cross = self._get_best_crossing(freq_log, gain_log, 0.0)
        if not cross:
            return 0.0
        return 10**ugbw_log

    
    def find_phm(self, freq, vout):
        """
        TODO: Implement the phase margin (PHM) calculation
        """
        ugbw = self.find_ugbw(freq,vout)
        if ugbw == 0.0:
            return 0.0
        #unwrap assumes radians so degree outside
        phase_deg = np.degrees(np.unwrap(np.angle(vout)))
        phase_ugbw = np.interp(np.log10(ugbw), np.log10(freq), phase_deg) 
        phm = 180 + phase_ugbw  
        return phm
        
    
    def find_slew_rate(self, time, signal, threshold_low=0.1, threshold_high=0.9, time_unit='us'):
        """
        TODO: Implement the slew rate calculation
        """
        signal_min = np.min(signal)
        signal_max = np.max(signal)
        swing = signal_max - signal_min
        if swing <=0:
            return 0.0
        signal_low = signal_min + threshold_low * swing
        signal_high = signal_min + threshold_high * swing

        #rising edge
        t_rise_low, i = self._time_to_cross_threshold(time, signal, signal_low, 0, True)
        if t_rise_low is None:
            return 0.0
        t_rise_high, _ = self._time_to_cross_threshold(time, signal, signal_high, i, True)

        #falling edge
       #t_fall_high, j = self._time_to_cross_threshold(time, signal, signal_high, 0, False)
        #if t_fall_high is None:
          #  return 0.0
        #t_fall_low, _ = self._time_to_cross_threshold(time, signal, signal_low, j, False)

        if t_rise_high is None:
            return 0.0
        
        sr_rise = (signal_high - signal_low) / (t_rise_high - t_rise_low)
        #sr_fall = (signal_high - signal_low) / (t_fall_low - t_fall_high)
        #sr = min(sr_rise, sr_fall)

        unit_scale = {'s': 1.0, 'ms': 1e-3, 'us': 1e-6, 'ns': 1e-9}
        return sr_rise * unit_scale[time_unit]

    def _time_to_cross_threshold(self, time, signal, signal_level, start, rising):
        for i in range(start, len(signal) - 1):
            xi = signal[i]
            yi = signal[i + 1]
            if (rising and xi<signal_level<=yi) or (not rising and xi>signal_level>=yi):
                fraction = (signal_level-xi) / (yi-xi)
                return time[i] + fraction * (time[i + 1] - time[i]), i
        return None, None

    def _get_best_crossing(cls, xvec, yvec, val):
        interp_fun = interp.InterpolatedUnivariateSpline(xvec, yvec, k=min(3, len(xvec)-1))

        def fzero(x):
            return interp_fun(x) - val

        xstart, xstop = xvec[0], xvec[-1]
        try:
            return sciopt.brentq(fzero, xstart, xstop), True
        except ValueError:
            return xstop, False