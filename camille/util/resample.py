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


def resample(series, onto=None, interp='linear'):
    """Resample

    Resample series onto another index, series or data frame

    Parameters
    ----------
    series : pandas.Series
        Series to resample
    onto : {pandas.Index, pandas.Series, pandas.DataFrame}
    interp : str, optional
        Interpolation method. Available methods:

        - :code:`prev`
        - :code:`next`
        - :code:`linear`
        - :code:`time`
        - :code:`index`
        - :code:`values`
        - :code:`nearest`
        - :code:`zero`
        - :code:`slinear`
        - :code:`quadratic`
        - :code:`cubic`
        - :code:`barycentric`
        - :code:`krogh`
        - :code:`polynomial`
        - :code:`spline`
        - :code:`piecewise_polynomial`
        - :code:`from_derivatives`
        - :code:`pchip`
        - :code:`akima`

    Returns
    -------
    pandas.Series
        `series` resampled onto the new index

    Raises
    ------
    ValueError
        If `interp` does not match a supported interpolation method

    Examples
    --------

    Resample series `a` onto series `b`

    >>> c = camille.util.resample(a, onto=b)
    >>> c.index.equals(b.index)
    True

    Resample series `a` onto data frame `df` using nearest neightbour
    interpolation

    >>> b = camille.util.resample(a, onto=df, interp='nearest')
    >>> b.index.equals(df.index)
    True

    Resample series `a` onto datetime index `idx`

    >>> idx = pd.DatetimeIndex([
    ...     datetime.datetime(2018, 1, 1, 0, 0, 0, tzinfo=pytz.utc),
    ...     datetime.datetime(2018, 1, 1, 0, 0, 1, tzinfo=pytz.utc),
    ...     datetime.datetime(2018, 1, 1, 0, 0, 2, tzinfo=pytz.utc),
    ...     datetime.datetime(2018, 1, 1, 0, 0, 3, tzinfo=pytz.utc),
    ... ])
    >>> b = camille.util.resample(a, onto=idx)
    >>> b.index
    DatetimeIndex(['2018-01-01 00:00:00+00:00', '2018-01-01 00:00:01+00:00',
                   '2018-01-01 00:00:02+00:00', '2018-01-01 00:00:03+00:00'],
                  dtype='datetime64[ns, UTC]', freq=None)
    """
    try:
        idx = onto.index
    except AttributeError:
        idx = onto

    ts = (
        pd.concat([series, pd.Series(index=idx, dtype=series.dtype)])
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
