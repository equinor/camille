#!/usr/bin/env python
import numpy as np
import pandas as pd

from camille import process

def test_process():
    index = pd.date_range('1/1/2018', periods=100, freq='S')

    t = np.linspace(-np.pi, np.pi, num=100)
    signal = np.sin(t)
    signal[40] *= 5   #create an outlier

    s = pd.Series(signal, index=index)
    dt = pd.Timedelta(seconds=5)

    processed = process.rolling_median(s, wsize=dt)

    expected = s.drop(s.index[40]).iloc[5:-5]
    pd.testing.assert_series_equal(expected, processed)
