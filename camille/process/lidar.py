from math import acos, atan2, cos, sin, tan, log, sqrt, radians
import numpy as np
import pandas as pd


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
    # scale = (cos(zn) * sin(pitch) +
    #         -sin(zn) * cos(azm) * cos(pitch) * sin(roll) +
    #          sin(zn) * sin(azm) * cos(pitch) * cos(roll))
    # The above collapsed to this:
    scale = sin(zn) * cos(pitch) * sin(azm - roll) + cos(zn) * sin(pitch)
    return hub_hgt + lidar_hgt + (dist / cos(zn)) * scale


def planar_windspeed_cmr(rws_a, rws_b, pitch, roll, azm, zn):
    """Planar windspeed

    .. warning:: This function is incorrect and only produces correct results
                 when roll = 0

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
        Planar wind speed reconstructed from rws_a and rws_b
    """
    # x_divisor = 2 * (cos(zn) * cos(pitch) +
    #                  sin(zn) * cos(azm) * sin(pitch) * sin(roll) -
    #                  sin(zn) * sin(azm) * sin(pitch) * cos(roll))
    # The above collapsed to this:
    xdiv = 2 * (cos(zn) * cos(pitch) - sin(pitch) * sin(zn) * sin(azm - roll))
    x = (rws_a + rws_b) / xdiv
    y = (rws_a - rws_b) / (2 * sin(zn) * cos(azm) * cos(roll))
    return sqrt(x ** 2 + y ** 2)


def planar_windspeed(rws_a, rws_b, pitch, roll, azm_a, azm_b, zn_a, zn_b):
    """Planar windspeed

    Calculates the wind speed for a horizontal plane given two beams, a and b. a
    being the leftmost beam  and b the  rightmost as seen from behind the LiDAR.
    The  vector and  orientation  of  the  beams are  given  by the pitch, roll,
    zeniths  and azimuths. Measured wind speeds are  given as  radial wind speed
    (RWS), that is the actual wind vector as projected onto the beam vector. The
    calculation is done by solving the following equations for V, where V is the
    wind vector:

    RWSa = R . La . V
    RWSb = R . Lb . V

    R is  the rotational  matrix Ry(pitch)  .  Rx(roll),  and  L are the LOS, or
    Line-Of-Sights, for beam a and b. The beam vector (RL) is given by:

                        Ry(p)                 Rx(r)                 L
                 | cos p  0  -sin p | | 1    0       0   | |      cos zn      |
    RL = R . L = |   0    1    0    | | 0  cos r   sin r | | sin zn * cos azm |
                 | sin p  0  cos p  | | 0  -sin r  cos r | | sin zn * sin azm |

    Because the wind speed is projected onto the beam, RL, we have:

               | Vx |
    RWS = RL . | Vy |
               | Vz |

    If we assume Vz to be 0, we get:

    RWSa = RLa_x * Vx + RLa_y * Vy
         = a * Vx + b * Vy
    RWSb = RLb_x * Vx + RLb_y * Vy
         = c * Vx + d * Vy

    Note that we rename RLa_x, RLa_y, RLb_x, and RLb_y to a, b, c, and d.

    Solving for Vx and Vy gives us:

    Vx = (b * RWSb - d * RWSa) / (b * c - d * a)
    Vy = (RWSa - a * Vx) / b

    The coordinate system is left-handed, X-forward, Y-right and Z-up.

    Parameters
    ----------
    rws_a : float
        Measured radial wind speed a
    rws_b : float
        Measured radial wind speed b
    pitch : float
    roll : float
    azm_a : float
        Line-of-sight a azimuth
    azm_b : float
        Line-of-sight b azimuth
    zn_a : float
        Line-of-sight a zenith
    zn_b : float
        Line-of-sight b zenith

    Returns
    -------
    float
        Planar wind speed reconstructed from rws_a and rws_b
    """
    a = (
        cos(pitch) * cos(zn_a) +
        cos(azm_a) * sin(pitch) * sin(roll) * sin(zn_a) -
        cos(roll) * sin(pitch) * sin(zn_a) * sin(azm_a)
    )
    b = cos(roll) * cos(azm_a) * sin(zn_a) + sin(roll) * sin(zn_a) * sin(azm_a)
    c = (
        cos(pitch) * cos(zn_b) +
        cos(azm_b) * sin(pitch) * sin(roll) * sin(zn_b) -
        cos(roll) * sin(pitch) * sin(zn_b) * sin(azm_b)
    )
    d = cos(roll) * cos(azm_b) * sin(zn_b) + sin(roll) * sin(zn_b) * sin(azm_b)
    x = (b * rws_b - d * rws_a) / (b * c - d * a)
    y = (rws_a - a * x) / b
    return sqrt(x ** 2 + y ** 2)


def shear_coefficient(ws_upr, ws_lwr, hgt_upr, hgt_lwr):
    """Shear Coefficient

    Calculate shear coefficient

    Parameters
    ----------
    ws_upr : float
        Wind speed of the upper plane
    ws_lwr : float
        Wind speed of the lower plane
    hgt_upr : float
        Height of the upper plane
    hgt_lwr : float
        Height of the lower plane

    Returns
    -------
    float
        Shear coefficient

    References
    ----------

    .. [1] https://en.wikipedia.org/wiki/Wind_profile_power_law
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
        DataFrame containing the measurements for this window, samples are
        assumed to be ordered by los id
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

    # IFP are using the same pitch for all measurements.
    # L.pitch = L.iloc[0].pitch

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

    if any(beam < 0 for beam in beam_hgts):
        raise ValueError('One or more beams are under ground/water.')

    rws = [L.loc[s].radial_windspeed for s in sensors]
    ws_upr = planar_windspeed(
        rws[0], rws[1], pitch_upr, roll_upr,
        azimuths[0], azimuths[1], zeniths[0],  zeniths[1])
    ws_lwr = planar_windspeed(
        rws[2], rws[3], pitch_lwr, roll_lwr,
        azimuths[2], azimuths[3], zeniths[2], zeniths[3])

    shear_coeff = shear_coefficient(ws_upr, ws_lwr, hgt_upr, hgt_lwr)
    hws = extrapolate_windspeed(hub_hgt, shear_coeff, ws_lwr, hgt_lwr)
    return hws, {
        'shear_coeff': shear_coeff,
        **{'rws{}'.format(s): rws[s] for s in sensors},
        **{'beam_hgt{}'.format(s): beam_hgts[s] for s in sensors},
        'planar_ws_upr': ws_upr,
        'planar_ws_lwr': ws_lwr,
        **{'time{}'.format(s): L.loc[s].time for s in sensors},
        **{'pitch{}'.format(s): L.loc[s].pitch for s in sensors},
        **{'roll{}'.format(s): L.loc[s].roll for s in sensors},
    }


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
        hub_hgt=98.6,
        lidar_hgt=4.5,
        pitch_offset=radians(-2.0),
        roll_offset=radians(0.4),
        predicate=default_predicate,
        extra_columns=None):
    """Process LiDAR

    Reconstruct horizontal wind speeds from Wind Iris real-time data

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing the LiDAR measurements. It is assumed that all
        samples in `df` are for the same distance
    dist : float
        The distance of the measurements
    hub_hgt : float, optional
        Nacelle hub height
    lidar_hgt : float, optional
        Height of the LiDAR
    pitch_offset : float, optional
    roll_offset : float, optional
    predicate : function (pandas.DataFrame) -> bool, optional
        Condition for deciding if a sample window is valid
    extra_columns : list of str, optional
        Export extra data. Sometimes it can be useful to export intermediate
        values computed by this processor. Available extra columns are:

        - :code:`shear_coeff` - Shear coefficient
        - :code:`rws[0-3]` - radial wind speeds
        - :code:`beam_hgt[0-3]` - beam heights
        - :code:`planar_ws_(upr|lwr)` - planar wind speeds
        - :code:`time[0-3]` - los sample times

    Returns
    -------
    pandas.DataFrame
        hws column contains the computed horizontal wind speeds
    """

    elevation = list(map(radians, [5.0, 5.0, -5.0, -5.0]))
    telescope = list(map(radians, [-15.0, 15.0, -15.0, 15.0]))
    zeniths = [acos(cos(elevation[i]) * cos(telescope[i])) for i in range(4)]
    azimuths = [atan2(sin(elevation[i]), tan(telescope[i])) for i in range(4)]

    if set(df.columns) < set(columns):
        raise ValueError('DataFrame columns must be {}'.format(columns))

    out_columns = ['hws']
    if extra_columns is not None:
        out_columns += list(extra_columns)

    df = df.copy()
    df.index.name = 'time'
    df.los_id = df.los_id.astype('int')
    df.pitch += pitch_offset
    df.roll += roll_offset

    index = df.index
    hws = pd.DataFrame(columns=out_columns, index=index, dtype=float)

    for i, k in zip(range(len(df)), range(4, len(df) + 1)):
        """
        We compute the horizontal windspeed using four LOS measurements. We
        therefor consider windows of size four.
        """

        win = df.iloc[i:k]
        time = win.index[0]

        if not predicate(win):
            hws.loc[time] = np.nan
            continue

        win.reset_index(inplace=True)
        win.set_index('los_id', inplace=True)
        win.sort_index(inplace=True)

        hws0, extra = (
            horiz_windspeed(win, dist, hub_hgt, lidar_hgt, azimuths, zeniths))

        row = [hws0]
        if extra_columns is not None:
            row += [extra[c] for c in extra_columns]
        hws.loc[time] = row

    return hws.dropna()
