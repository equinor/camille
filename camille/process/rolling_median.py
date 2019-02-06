import pandas as pd
import numpy as np

def process(signal, wsize, tolerance=None):
    """ Process rolling median

    Rolling window calculations

    Parameters
    ----------
    signal : pd.Series
    wsize : int or pd.Timedelta
        size of the rolling window
    tolerance : float, optional
        threshold for outliers, default to the standard deviation of signal

    Returns
    -------
    pd.Series
        filtered signal

    Examples
    --------
    >>> s = pd.Series(signal, index=t)
    >>> processed = process.rolling_median(s, wsize=20, tolerance=2.0)
    """

    dt = signal.index[1] - signal.index[0]
    if isinstance(wsize, pd.Timedelta):
        if wsize < dt:
            problem = "wsize is smaller than the samplerate of signal: {} < {}".format(wsize, dt)
            raise ValueError(problem)

        wsize = int(np.ceil(wsize / dt))

    if tolerance == None: tolerance = 1.0 * signal.std()

    rolling = signal.rolling(window=wsize, min_periods=1, center=True).median()
    outliers = signal[(signal - rolling).abs() >= tolerance]
    cleaned = signal.drop(outliers.index).iloc[wsize:-wsize]
    return cleaned
