import numpy as np
from camille.process import mooring_stress

def test_calculate_stress():
    signal = np.array([2, 1, 3, 2, 4])
    ref = np.array([0.07307389, 0.03653695, 0.10961084,
                    0.07307389, 0.14614779])
    stress = mooring_stress(signal, diameter=132)
    assert np.allclose(stress, ref)
