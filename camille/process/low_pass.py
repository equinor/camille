import pandas as pd
from scipy.signal import filtfilt, butter

def process(signal, sampling_rate, cutoff_freq, order=5):
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
    nyq_freq = 0.5 * sampling_rate
    normal_cutoff = cutoff_freq / nyq_freq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    lps = filtfilt(b, a, signal.values)
    return pd.Series(lps, index=signal.index)
