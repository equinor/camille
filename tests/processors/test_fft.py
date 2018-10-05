#!/usr/bin/env python
import pandas as pd
import numpy as np

from camille.process import fft

def test_fft():
    df = pd.DataFrame(np.random.normal(size=(100)))
    config = {'inverse': False}
    inv_config = {'inverse': True}
    spectrum = fft.process(df, **config)
    signal = fft.process(spectrum, **inv_config).apply(np.real)

    assert np.allclose(df, signal)


def test_fft2D():
    df = pd.DataFrame(np.random.normal(size=(100,10)))
    config = {'inverse': False}
    inv_config = {'inverse': True}
    spectrum = fft.process(df, **config)
    signal = fft.process(spectrum, **inv_config).apply(np.real)

    assert np.allclose(df, signal)
