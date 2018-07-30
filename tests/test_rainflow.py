#!/usr/bin/env python
import unittest
import numpy as np
import pandas as pd
import rainflow

from camille import mooring_fatigue

refcase = [0.60727647, 0.14653493, 0.19643957, 0.56821631, 0.88833878, 0.29612997,
           0.59539649, 0.6996683, 0.10524973, 0.12334626, 0.68401331, 0.85985292,
           0.73141117, 0.36808646, 0.94015761, 0.85626572, 0.76956161, 0.49777263,
           0.54066458, 0.45931667, 0.82204694, 0.76816398, 0.66417278, 0.62238591,
           0.61302659, 0.0158001, 0.35254166, 0.54150519, 0.14868205, 0.91848263,
           0.8989403, 0.90866213, 0.831834, 0.48128077, 0.60999729, 0.78850529,
           0.67725795, 0.76098028, 0.96626931, 0.91693159, 0.19347573, 0.4920361,
           0.16060596, 0.10603582, 0.0017221, 0.6250337, 0.43623379, 0.54612575,
           0.00411415, 0.91371242, 0.08600793, 0.77993431, 0.89695114, 0.43309567,
           0.70051438, 0.05484055, 0.0673957, 0.68068416, 0.12452928, 0.00811467,
           0.33861137, 0.61719287, 0.49407856, 0.8300253, 0.29934456, 0.7107892,
           0.38225825, 0.02715285, 0.0189073, 0.68926121, 0.46134276, 0.25709821,
           0.46942654, 0.68086762, 0.3117921, 0.89299606, 0.43332419, 0.04576419,
           0.09044587, 0.28137508, 0.365343, 0.94461639, 0.48949621, 0.03472242,
           0.79210514, 0.94612641, 0.25696703, 0.61546048, 0.04270415, 0.6681445,
           0.79452558, 0.41156153, 0.4671666, 0.01783284, 0.8529705, 0.56580293,
           0.62133836, 0.74723755, 0.28597705, 0.7421038]

cycle_ref = [0.5000, 1.0000, 0.5000, 1.0000, 0.5000, 1.0000,
             1.0000, 0.5000, 1.0000, 1.0000, 1.0000, 1.0000,
             0.5000, 1.0000, 0.5000, 1.0000, 1.0000, 1.0000,
             1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000,
             1.0000, 1.0000, 1.0000, 1.0000, 1.0000, 1.0000,
             1.0000, 1.0000, 0.5000, 0.5000, 0.5000, 0.5000,
             0.5000, 0.5000]

amp_ref = [0.2304, 0.2018, 0.3709, 0.2459, 0.3915, 0.0214,
           0.1814, 0.4175, 0.1964, 0.0049, 0.0556, 0.2186,
           0.4622, 0.1493, 0.4752, 0.0549, 0.3105, 0.1337,
           0.4055, 0.3129, 0.0616, 0.2057, 0.1845, 0.2161,
           0.4056, 0.4236, 0.4528, 0.4549, 0.1792, 0.0278,
           0.3759, 0.0907, 0.4823, 0.4722, 0.4641, 0.4176,
           0.2835, 0.2281]

mean_ref = [0.3769, 0.4979, 0.5174, 0.6140, 0.4968, 0.5192,
            0.6407, 0.5227, 0.3451, 0.9038, 0.7329, 0.6999,
            0.4780, 0.3428, 0.4910, 0.4912, 0.3146, 0.5668,
            0.4915, 0.3678, 0.5556, 0.5051, 0.4963, 0.4732,
            0.4245, 0.4694, 0.4609, 0.4897, 0.4362, 0.4394,
            0.4186, 0.6565, 0.4840, 0.4739, 0.4820, 0.4354,
            0.5695, 0.5140]


class TestRainflow(unittest.TestCase):
    def test_process(self):
        d = {'bridle1': refcase}
        df = pd.DataFrame(data=d)
        res = mooring_fatigue.process(df, window=1, fs=5)
        assert res is not None


    def test_rainflowlib(self):
        cycles = []
        means = []
        amplitudes = []
        for low, high, mult in rainflow.extract_cycles(refcase, True, True):
            cycles.append(mult)

            mean = 0.5 * (high + low)
            means.append(mean)

            amplitude = high - 0.5 * (high + low)
            amplitudes.append(amplitude)

        assert np.array_equal(cycles, cycle_ref)
        assert np.array_equal(np.round(means, 4), mean_ref)
        assert np.array_equal(np.round(amplitudes, 4), amp_ref)


    def test_calc_damage(self):
        damage = mooring_fatigue._calc_damage(refcase)
        assert damage == 1.0400195722392278e+18


    def test_nan(self):
        data = [np.nan, 0, 0, 2, np.nan]
        is_bad = mooring_fatigue._is_bad_data(data, 100)
        assert is_bad


    def test_valid(self):
        data = [1, 0, 0, 2, 1]
        is_bad = mooring_fatigue._is_bad_data(data, 100)
        assert not is_bad


    def test_sudden_jump(self):
        data = [0, 0, 0, 1000, 0]
        is_bad = mooring_fatigue._is_bad_data(data, 100)
        assert is_bad


    def test_constant(self):
        data = [1, 1, 1, 1, 1]
        is_bad = mooring_fatigue._is_bad_data(data, 100)
        assert is_bad


    def test_calculate_stress(self):
        signal = np.array([2, 1, 3, 2, 4])
        ref = np.array([0.07307389, 0.03653695, 0.10961084, 0.07307389, 0.14614779])
        stress = mooring_fatigue._calculate_stress(signal)
        assert np.allclose(stress, ref)


if __name__ == '__main__':
    unittest.main()
