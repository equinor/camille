#!/usr/bin/env python
import pandas as pd
import numpy as np

from camille import process

def test_fft():
    df = pd.DataFrame(np.random.normal(size=(100)))
    spectrum = process.fft(df, inverse=False)
    signal = process.fft(spectrum, inverse=True).apply(np.real)

    assert np.allclose(df, signal)


def test_fft2D():
    df = pd.DataFrame(np.random.normal(size=(100,10)))
    spectrum = process.fft(df, inverse=False)
    signal = process.fft(spectrum, inverse=True).apply(np.real)

    assert np.allclose(df, signal)
