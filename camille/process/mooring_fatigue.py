import math

import numpy as np
import rainflow
import pandas as pd
from camille.util import sn_curve

def process(series, window_length=3600, fs=5):
    """Calculate fatigue damage

    Parameters
    ----------
    series : pandas.Series
        Bridle tension [kN]
    window_length : int, optional
        Length of each window for fatige calculations [s]
    fs : int or float, optional
        Sampling frequency [1/s]

    Returns
    -------
    pandas.Series
    """

    samples = series.size
    window = math.ceil(window_length * fs)
    n_windows = math.floor(samples / window)

    damage = np.empty(n_windows)

    for w in range(0, n_windows):
        start_idx, end_idx = w * window, (w + 1) * window
        data = series.iloc[start_idx:end_idx]

        if _is_bad_data(data, 100):
            damage[w] = np.nan
            continue

        stress = _calculate_stress(data)
        dmg = _calc_damage(stress)
        seconds_per_year = 3600 * 24 * 365
        dmb_calc = seconds_per_year / window_length * dmg
        damage[w] = dmb_calc

    return pd.Series(damage)


def _calculate_stress(data):
    A = 2 * math.pi / 4 * 132e-3 ** 2  # 132mm chain
    return 1e-3 * data / A  # Tension (in kN) converted to MPa


def _calc_damage(data):
    stress_ranges = []
    cycles = []
    for low, high, mult in rainflow.extract_cycles(data, True, True):
        cycles.append(mult)
        amplitude = high - 0.5 * (high + low)
        if amplitude > 0: stress_ranges.append( 2*amplitude )

    N = sn_curve(stress_ranges, logA=math.log10(6e10), m=3, t=0, tref=25, k=0)
    damage = sum(sorted(cycles/N))
    return damage


def _is_bad_data(data, diff_limit):
    TOL = 1e-12
    diff_d = np.diff(data)
    max_d = np.max(np.abs(diff_d))

    return max_d > diff_limit or (np.abs(max_d) < TOL or np.isnan(data).any())
