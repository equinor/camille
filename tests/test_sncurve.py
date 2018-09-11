#!/usr/bin/env python
from camille.utils.sncurves import sn_curve
import numpy as np

def test_scalar_params():
    x = [ 12.73, 47.83, 41.05, 30.05, 24.58 ]
    expected = [ 2.90847971e7, 5.48340227e5, 8.67384717e5,
                 2.21114804e6, 4.04022558e6 ]

    result = sn_curve( x,
                       logA=np.log10(6e10),
                       m=3, t=0,
                       tref=25,
                       k=0 )

    assert np.allclose(result, expected)

def test_array_params():
    x = [ 22.49, 25.13, 4.83, 30.44]
    expected = [ 3.63122134e9, 2.08467115e9, 7.94811873e12, 7.99423221e8 ]

    result = sn_curve( x,
                       logA=[12.192,16.32],
                       m=[3.0,5.0],
                       k=0.05,
                       tref=25,
                       t=0 )

    assert np.allclose(result, expected)
