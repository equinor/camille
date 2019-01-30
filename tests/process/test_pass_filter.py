#!/usr/bin/env python
import pandas as pd
import numpy as np
from numpy import pi
from scipy.fftpack import fft
from scipy.signal import find_peaks
from camille import process


def _pass_filter(filter_func, cutoff):
    sampling_rate = 3000.0
    signal_duration = 0.05
    n_samples = int(signal_duration * sampling_rate)

    t = np.linspace(0, signal_duration, n_samples, endpoint=False)
    f1, f2, f3, f4 = 300, 700.0, 1200.0, 1400

    signal = 1.1 * np.sin(f1 * 2 * pi * t + 0.3)
    signal += 0.6 * np.sin(f2 * 2 * pi * t + 0.5)
    signal += 1.3 * np.sin(f3 * 2 * pi * t + 1.1)
    signal += 1.4 * np.sin(f4 * 2 * pi * t)
    s = pd.Series(signal, index=t)

    ps = filter_func(s, sampling_rate, cutoff, order=10)

    half_samples = n_samples // 2
    orig_freqs = np.abs(fft(s.values)[0:half_samples])
    ps_freqs = np.abs(fft(ps.values)[0:half_samples])

    min_peak_h = 10
    orig_peaks, _ = find_peaks(orig_freqs, height=min_peak_h)
    ps_peaks, _ = find_peaks(ps_freqs, height=min_peak_h)

    freq_bin_s = sampling_rate // n_samples
    pd.testing.assert_index_equal(s.index, ps.index)

    return freq_bin_s * ps_peaks, [f1, f2, f3, f4]


def test_lowpass():
    filtered_peaks, orig_peaks = _pass_filter(process.low_pass, 850)
    np.testing.assert_array_equal(filtered_peaks, orig_peaks[0:2])


def test_bandass():
    filtered_peaks, orig_peaks = _pass_filter(process.band_pass, [500, 900])
    np.testing.assert_array_equal(filtered_peaks, orig_peaks[1:2])


def test_highpass():
    filtered_peaks, orig_peaks = _pass_filter(process.high_pass, 850)
    np.testing.assert_array_equal(filtered_peaks, orig_peaks[2:4])
