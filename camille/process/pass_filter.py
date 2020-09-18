import pandas as pd
from scipy.signal import filtfilt, butter


def _pass_filter(signal, sampling_rate, filter_type, cutoff_freq, order=5):
    nyq_freq = 0.5 * sampling_rate
    normal_cutoff = [x / nyq_freq for x in cutoff_freq]
    b, a = butter(order, normal_cutoff, btype=filter_type, analog=False)
    lps = filtfilt(b, a, signal.values)
    return pd.Series(lps, index=signal.index)


def low_pass(signal, sampling_rate, cutoff_freq, order=5):
    """Process low pass

    Remove high frequencies from signal

    Parameters
    ----------
    signal : pandas.Series
    sampling_rate : float
    cutoff_freq : float
        Cutoff frequency. Higher frequencies will be removed from signal
    order : int, optional
        Order of the Butterworth filter

    Returns
    -------
    pd.Series
        Lower-frequency signal

    Examples
    --------
    >>> s = pd.Series(signal, index = t)
    >>> processed = process.low_pass(s, 48000, 8000.0, order=8)
    """
    return _pass_filter(signal, sampling_rate, 'lowpass', [cutoff_freq], order)


def high_pass(signal, sampling_rate, cutoff_freq, order=5):
    """Process high pass

    Remove low frequencies from signal

    Parameters
    ----------
    signal : pandas.Series
    sampling_rate : float
    cutoff_freq : float
        Cutoff frequency. Lower frequencies will be removed from signal
    order : int, optional
        Order of the Butterworth filter

    Returns
    -------
    pd.Series
        Higher-frequency signal

    Examples
    --------
    >>> s = pd.Series(signal, index = t)
    >>> processed = process.high_pass(s, 48000, 2000.0, order=8)
    """
    return _pass_filter(signal, sampling_rate, 'highpass', [cutoff_freq], order)


def band_pass(signal, sampling_rate, cutoff_freq, order=5):
    """Process band pass

    Remove low and high frequencies from signal

    Parameters
    ----------
    signal : pandas.Series
    sampling_rate : float
    cutoff_freq : array_like
        2-length array of cutoff frequencies [low_cutoff_freq, high_cutoff_freq]
    order : int, optional
        Order of the Butterworth filter

    Returns
    -------
    pd.Series
        Higher-frequency signal

    Examples
    --------
    >>> s = pd.Series(signal, index = t)
    >>> processed = process.band_pass(s, 48000, [2000.0, 8000.0], order=8)
    """
    return _pass_filter(signal, sampling_rate, 'bandpass', cutoff_freq, order)
