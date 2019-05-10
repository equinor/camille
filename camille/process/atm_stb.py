import math


def process(deltatemp):
    """Process atmospheric stability

    Classify atmospheric stability based on `deltatemp`

    Parameters
    ----------
    deltatemp : pandas.Series
        Temperature difference

    Returns
    -------
    pandas.Series
        Atmospheric stability series
    """
    atm_stb = deltatemp.apply(_atm_stb)
    atm_stb.rename('atm_stb', inplace=True)
    return atm_stb


def _atm_stb(delta_temp):
    """Atmospheric stability

    Parameters
    ----------
    delta_temp : number
        Difference between ambient and sea temperatures

    Returns
    -------
    str
        Atmospheric stability classification
    """
    if not delta_temp or math.isnan(delta_temp): return 'Missing Data'
    if 5.0 <= delta_temp         : return 'Very Unstable'
    if 2.5 <= delta_temp <   5.0 : return 'Unstable'
    if 0.5 <= delta_temp <   2.5 : return 'Slightly Unstable'
    if -0.5 < delta_temp <   0.5 : return 'Neutral'
    if -2.5 < delta_temp <= -0.5 : return 'Slightly Stable'
    if -5.0 < delta_temp <= -2.5 : return 'Stable'
    if        delta_temp <= -5.0 : return 'Very Stable'
