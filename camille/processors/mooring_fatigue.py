import math

import numpy
import rainflow
import sncurves


def process(df, **kwargs):
    options = ('window', 'fs')
    if not all([key in options for key in kwargs.keys()]):
        raise ArgumentError('Unknown argument(s) {}'.format(kwargs.keys() - options))
    window_length = kwargs.get('window', 3600)  # Length of each window for fatigue calculations [s]
    fs = kwargs.get('fs', 5)

    samples = len(df)
    window = math.ceil(window_length * fs)
    n_windows = math.floor(samples / window)

    df['damage'] = 0
    df['bad'] = False

    # Loop the windows
    for w in range(0, n_windows):
        start_idx, end_idx = w * window, (w + 1) * window
        data = df.ix[:,0].iloc[start_idx:end_idx]

        if _is_bad_data(data, 100):
            df['bad'].iloc[start_idx:end_idx] = True
            continue

        stress = _calculate_stress(data)
        dmg = _calc_damage(stress)
        df['damage'].iloc[start_idx:end_idx] = dmg
    return df


def _calculate_stress(data):
    # Calculate stress
    A = 2 * math.pi / 4 * 132e-3 ** 2  # 132mm chain
    return 1e-3 * data / A  # Tension (in kN) converted to MPa


def _calc_damage(data):
    rf = rainflow.count_cycles(data, left=True, right=True)
    stress_ranges = [tup[0] for tup in rf if tup[0] > 0]
    sn = sncurves.get_sn_curve("C1", seawater=True, cp=False)
    N = sn(stress_ranges)
    damage = sum(N)
    return damage


def _is_bad_data(data, diff_limit):
    TOL = 1e-12
    diff_d = numpy.diff(data)
    max_d = numpy.max(numpy.abs(diff_d))
    if max_d > diff_limit or (numpy.abs(max_d) < TOL or numpy.isnan(data).any()):
        return True
    return False
