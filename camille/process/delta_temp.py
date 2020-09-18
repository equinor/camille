def process(amb, sea):
    """Process temperatures delta

    Parameters
    ----------
    amb : pandas.Series
        Ambient temperature
    sea : pandas.Series
        Sea temperature

    Returns
    -------
    pandas.Series
        Difference between provided series resampled per 20 minutes
    """
    delta_temp = sea.resample('20T').mean() - amb.resample('20T').mean()
    delta_temp.rename('delta_temp', inplace=True)
    return delta_temp
