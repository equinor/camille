#!/usr/bin/env python
import unittest
import pandas as pd
import numpy as np

class TestFFT(unittest.TestCase):

    def test_fft(self):
        from camille import fft
        df = pd.DataFrame(np.random.normal(size=(100)))
        config = {'inverse': False}
        inv_config = {'inverse': True}
        spectrum = fft.process(df, **config)
        signal = fft.process(spectrum, **inv_config).apply(np.real)

        pd.testing.assert_frame_equal(df, signal)

    def test_fft2D(self):
        from camille import fft
        df = pd.DataFrame(np.random.normal(size=(100,10)))
        config = {'inverse': False}
        inv_config = {'inverse': True}
        spectrum = fft.process(df, **config)
        signal = fft.process(spectrum, **inv_config).apply(np.real)

        pd.testing.assert_frame_equal(df, signal)


if __name__ == '__main__':
    unittest.main()
