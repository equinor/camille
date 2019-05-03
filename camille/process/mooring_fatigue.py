import math

import numpy as np
import rainflow
import pandas as pd
from scipy.interpolate import interp1d

def sncurve(stress, k=None, logA=None, m=None, t=0, tref=25.0):
    """SN Curve

    Computes the number of stress cycles before failure for the given stress.

    Parameters
    ----------
    stress : float or list of float
        Stress range [MPa]
    k : float
        Thickness exponent on fatigue strength
    logA : float or list of float
        Intercept of log N axis
    m : float or list of float
        Negative inverse slope of S-N curve
    t : float, optional
        Thickness [mm] through which a crack will most likely grow. t = tref is
        used for t < tref
    tref : float, optional
        Reference thickness [mm]

    Returns
    -------
    float or list of floats
        Number of stress cycles before failure

    """
    alpha = max((t / tref) ** k, 1)
    stress = np.array(stress) * alpha

    try:
        x = np.zeros(len(logA) + 1)
        y = np.zeros(len(logA) + 1)

        [x[0],x[-1]] = [12, -9]
        [y[0],y[-1]] = [logA[0] - m[0] * 12, logA[-1] + m[ - 1] * 9]

        for i in range(len(logA)-1, 0, -1):
            x[i] = (logA[i] - logA[i - 1]) / (m[i] - m[i - 1])
            y[i] = logA[i] - m[i] * x[i]

    except TypeError:
        x = np.array([12, -9])
        y = np.array([logA - m * 12, logA + m * 9])

    interp = interp1d(x, y, kind='linear', fill_value='extrapolate')

    return 10 ** interp(np.log10(stress))


def process(series, window_length=3600, fs=5, sn_curve=None):
    """Calculate fatigue damage
    Note, that if in the last bin there is not enough data
    for calculations, it's skipped.

    Parameters
    ----------
    series : pandas.Series
        Bridle tension [kN]
    window_length : int, optional
        Length of each window for fatigue calculations [s]
    fs : int or float, optional
        Sampling frequency [1/s]
    sn_curve : dict
        Dict containing parameters for the sncurve (function that computes
        number of cycles to failure for a given stress).

        k : float
            Thickness exponent on fatigue strength
        logA : float or list of float
            Intercept of log N axis
        m : float or list of float
            Negative inverse slope of S-N curve
        t : float, optional
            Thickness [mm] through which a crack will most likely grow.
            t = tref is used for t < tref
        tref : float, optional
            Reference thickness [mm]

    Returns
    -------
    pandas.Series
        Damage calculations for the given windows. Data is indexed
        using the window left boundary index.
    """

    samples = series.size
    window = math.ceil(window_length * fs)
    n_windows = math.floor(samples / window)

    damage = np.empty(n_windows)
    index = []

    for w in range(0, n_windows):
        start_idx, end_idx = w * window, (w + 1) * window
        data = series.iloc[start_idx:end_idx]
        index.append(series.index[start_idx])

        if _is_bad_data(data, 100):
            damage[w] = np.nan
            continue

        stress = _calculate_stress(data)
        dmg = _calc_damage(stress, sn_curve)
        seconds_per_year = 3600 * 24 * 365
        dmb_calc = seconds_per_year / window_length * dmg
        damage[w] = dmb_calc

    return pd.Series(damage, index=index)


def _calculate_stress(data):
    A = 2 * math.pi / 4 * 132e-3 ** 2  # 132mm chain
    return 1e-3 * data / A  # Tension (in kN) converted to MPa


def _calc_damage(data, sn_curve):
    stress_ranges = []
    cycles = []
    for low, high, mult in rainflow.extract_cycles(data, True, True):
        amplitude = high - 0.5 * (high + low)
        if amplitude > 0:
            cycles.append(mult)
            stress_ranges.append( 2*amplitude )

    N = sncurve(stress_ranges, **sn_curve)
    damage = sum(sorted(cycles/N))
    return damage


def _is_bad_data(data, diff_limit):
    TOL = 1e-12
    diff_d = np.diff(data)
    max_d = np.max(np.abs(diff_d))

    return max_d > diff_limit or (np.abs(max_d) < TOL or np.isnan(data).any())
