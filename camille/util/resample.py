import pandas as pd


_pandas_supported_interps = [
    'linear',
    'time',
    'index',
    'values',
    'nearest',
    'zero',
    'slinear',
    'quadratic',
    'cubic',
    'barycentric',
    'krogh',
    'polynomial',
    'spline',
    'piecewise_polynomial',
    'from_derivatives',
    'pchip',
    'akima',
]


def rm_dupl_indices(ts):
    return ts[~ts.index.duplicated(keep='first')]


def resample(tseries, onto=None, interp='linear'):
    try:
        idx = onto.index
    except:
        idx = onto

    ts = (
        pd.concat([tseries, pd.Series(index=idx)])
        .sort_index(kind='mergesort')
        )

    if interp in _pandas_supported_interps:
        ts = ts.interpolate(method=interp)
        return rm_dupl_indices(ts).reindex(idx)
    elif interp == 'prev':
        ts = ts.ffill()
        return rm_dupl_indices(ts).reindex(idx)
    elif interp == 'next':
        ts = ts.bfill()
        return rm_dupl_indices(ts).reindex(idx)
    else:
        raise ValueError('Unsupported interpolation scheme: {}'.format(interp))
