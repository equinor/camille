from math import cos, sin, log, sqrt, radians

import pandas as pd
import numpy as np


def sample_hgt(i, hub_hgt, lidar_hgt, dist, pitch, roll, azm, zn):
    """Sample height

    Parameters
    ----------
    hub_hgt : float
        Nacelle hub height
    lidar_hgt : float
        Height of the LiDAR
    dist : float
        Measurement distance
    pitch : float
    roll : float
    azm : float
        Line-of-sight azimuth
    zn : float
        Line-of-sight zenith

    Returns
    -------
    float
        Height of the beam for line-of-sight `i` at distance `dist`
    """
    sign = -1 if i >= 2 else 1
    return hub_hgt + lidar_hgt + dist * (
        cos(zn) * sin(pitch) +
        sign * sin(zn) * cos(azm) * cos(pitch) * sin(roll) +
               sin(zn) * sin(azm) * cos(pitch) * cos(roll))


def planar_windspeed(rws_a, rws_b, pitch, roll, azm, zn):
    """Planar windspeed

    Parameters
    ----------
    rws_a : float
        Radial wind speed a
    rws_b : float
        Radial wind speed b
    pitch : float
    roll : float
    azm : float
        Line-of-sight azimuth
    zn : float
        Line-of-sight zenith

    Returns
    -------
    float
        Planar wind speed interpolated between rws_a and rws_b
    """
    x_divisor = 2 * (cos(zn) * cos(pitch) +
                     sin(zn) * cos(azm) * sin(pitch) * sin(roll) -
                     sin(zn) * sin(azm) * sin(pitch) * cos(roll))
    x = (rws_a + rws_b) / x_divisor
    y = (rws_a - rws_b) / (2 * sin(zn) * cos(azm) * cos(roll))
    return sqrt(x ** 2 + y ** 2)


def shear_coefficient(ws_upr, ws_lwr, hgt_upr, hgt_lwr):
    """Extrapolate windspeed

    Parameters
    ----------
    hgt : float
        Target height
    shear_coeff : float
        Shear coefficient
    ref_windspeed : float
        Reference wind speed
    ref_hgt : float
        Reference height

    Returns
    -------
    float
        Wind speed at target height
    """
    return log(ws_upr / ws_lwr) / log(hgt_upr / hgt_lwr)


def extrapolate_windspeed(hgt, shear_coeff, ref_windspeed, ref_hgt):
    """Extrapolate windspeed

    Extrapolate windspeed using the wind profile power law [1]_.

    Parameters
    ----------
    hgt : float
        Target height
    shear_coeff : float
        Shear coefficient
    ref_windspeed : float
        Reference wind speed
    ref_hgt : float
        Reference height

    Returns
    -------
    float
        Wind speed at target height

    References
    ----------

    .. [1] https://en.wikipedia.org/wiki/Wind_profile_power_law
    """
    return ref_windspeed * pow(hgt / ref_hgt, shear_coeff)


def horiz_windspeed(L, dist, hub_hgt, lidar_hgt, azimuths, zeniths):
    """Horizontal wind speed

    Parameters
    ----------
    L : pandas.DataFrame
        DataFrame containing the measurements for this window
    dist : float
        Measurement distance
    hub_hgt : float
        Nacelle hub height
    lidar_hgt : float
        Height of the LiDAR
    azimuths : list of float
        Line-of-sight azimuths
    zeniths : list of float
        Line-of-sight zeniths

    Returns
    -------
    float
        Wind speed at nacelle hub height
    """
    sensors = L.index.tolist()
    pitch_upr = (L.loc[0].pitch + L.loc[1].pitch) / 2.0
    pitch_lwr = (L.loc[2].pitch + L.loc[3].pitch) / 2.0
    roll_upr = (L.loc[0].roll + L.loc[1].roll) / 2.0
    roll_lwr = (L.loc[2].roll + L.loc[3].roll) / 2.0

    beam_hgts = [
        sample_hgt(s, hub_hgt, lidar_hgt, dist,
                   L.loc[s].pitch, L.loc[s].roll, azimuths[s], zeniths[s])
        for s in sensors
    ]
    hgt_upr = (beam_hgts[0] + beam_hgts[1]) * 0.5
    hgt_lwr = (beam_hgts[2] + beam_hgts[3]) * 0.5

    rws = [L.loc[s].radial_windspeed for s in sensors]
    ws_upr = planar_windspeed(
        rws[0], rws[1], pitch_upr, roll_upr, azimuths[0], zeniths[0])
    ws_lwr = planar_windspeed(
        rws[2], rws[3], pitch_lwr, roll_lwr, azimuths[2], zeniths[2])

    shear_coeff = shear_coefficient(ws_upr, ws_lwr, hgt_upr, hgt_lwr)
    return extrapolate_windspeed(hub_hgt, shear_coeff, ws_lwr, hgt_lwr)


# Predicates

def ordered_los_id_4(df):
    """Ordered line-of-sight id 4

    Helper predicate for sample validation

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing the measurements for this window

    Returns
    -------
    bool
        True if the los_ids of `df` exactly 0, 1, 2, and 3 in order
    """
    return df.los_id.tolist() == [0, 1, 2, 3]


def los_id_4(df):
    """Line-of-sight id 4

    Helper predicate for sample validation

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing the measurements for this window

    Returns
    -------
    bool
        True if `df` contains los_ids 0, 1, 2, and 3
    """
    return set(df.los_id) == set([0, 1, 2, 3])


def all_ok(df):
    """Line-of-sight id 4

    Helper predicate for sample validation

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing the measurements for this window

    Returns
    -------
    bool
        True if the status of all measurements are 1
    """
    return (df.status == 1).all()


def max_duration(df, max_seconds=5.0):
    """Maximum duration

    Helper predicate for sample validation

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing the measurements for this window
    max_seconds : float
        The maximal time difference for the measurements

    Returns
    -------
    bool
        True if the duration of `df` is less than `max_seconds`
    """
    duration = df.index.max().to_pydatetime() - df.index.min().to_pydatetime()
    return duration.total_seconds() < max_seconds


def default_predicate(df):
    """Default predicate

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing the measurements for this window

    Returns
    -------
    bool
        True if `df` contains measurements ordered 0 to 3, all measurements have
        status 1, and the duration of `df` does not exceed 5 seconds
    """
    return ordered_los_id_4(df) and all_ok(df) and max_duration(df, 5.0)


# Process

columns = ('los_id', 'radial_windspeed', 'status', 'pitch', 'roll')

def process(
        df,
        dist,
        azimuths=None,
        zeniths=None,
        hub_hgt=98.6,
        lidar_hgt=4.5,
        pitch_offset=radians(-2.0),
        roll_offset=radians(0.4),
        predicate=default_predicate):
    """Process LiDAR

    Reconstruct horizontal wind speeds from Wind Iris real-time data

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing the LiDAR measurements. It is assumed that all
        samples in `df` are for the same distance
    dist : float
        The distance of the measurements
    azimuths : list of float, optional
        Line-of-sight azimuths
    zeniths : list of float, optional
        Line-of-sight zeniths
    hub_hgt : float, optional
        Nacelle hub height
    lidar_hgt : float, optional
        Height of the LiDAR
    pitch_offset : float, optional
    roll_offset : float, optional
    predicate : function (pandas.DataFrame) -> bool, optional
        Condition for deciding if a sample window is valid

    Returns
    -------
    pandas.TimeSeries
        Computed horizontal wind speeds
    """

    if azimuths is None:
        azimuths = list(map(radians, [18.0181, 161.9819, -18.0181, -161.9819]))
    if zeniths is None:
        zeniths = list(map(radians, [15.79, 15.79, 15.79, 15.79]))

    if set(df.columns) <= set(columns):
        raise ValueError('DataFrame columns must be {}'.format(columns))

    df = df.copy() # Also copies the DataFrame
    df.pitch += pitch_offset
    df.roll += roll_offset

    index = df.index
    hws = pd.Series(name='value', index=index)

    for i, k in zip(range(len(df)), range(4, len(df)+1)):
        """
        We compute the horizontal windspeed using four LOS measurements. We
        therefor consider windows of size four.
        """

        win = df.iloc[i:k]
        time = win.index[0]
        if not predicate(win):
            hws.loc[time] = np.nan
            continue
        win = win.set_index('los_id').sort_index()
        hws0 = horiz_windspeed(win, dist, hub_hgt, lidar_hgt, azimuths, zeniths)
        hws.loc[time] = hws0

    return hws.dropna()
