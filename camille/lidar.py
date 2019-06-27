from . import core
from math import acos, atan2, cos, radians, sin, tan
import numpy as np
import pandas as pd

elevation = list(map(radians, [5.0, 5.0, -5.0, -5.0]))
telescope = list(map(radians, [-15.0, 15.0, -15.0, 15.0]))
zeniths  = [acos(cos(e) * cos(t)) for e, t in zip(elevation, telescope)]
azimuths = [atan2(sin(e), tan(t)) for e, t in zip(elevation, telescope)]


columns = ('los_id', 'radial_windspeed', 'status', 'pitch', 'roll')


def extrapolate_windspeed(df, height):
    """Extrapolate windspeed

    Extrapolate windspeed using the wind profile power law [1]_.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with measured speeds, heights and shears
        Required columns:
        - :code:`speed` - Wind speed
        - :code:`height` - Measurement height
        - :code:`shear` - Shear
    height : float
        The height at which to extrapolate the windspeed

    Returns
    -------
    pandas.Series
        Wind speed at target height

    References
    ----------
    .. [1] https://en.wikipedia.org/wiki/Wind_profile_power_law
    """
    hws = df.speed * np.power(height / df.height, df.shear)
    return hws


def extrapolate_winddirection(df, height):
    """Extrapolate wind direction

    Extrapolate wind direction using the linear law and veer

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe with measured directions, heights and veers
        Required columns:
        - :code:`dir` - Wind direction
        - :code:`height` - Measurement height
        - :code:`veer` - Veer
    height : float
        The height at which to extrapolate the wind direction

    Returns
    -------
    pandas.Series
        Wind direction at target height
    """
    hwd = df.dir + df.veer * (height - df.height)
    return hwd


def windfield_desc(df, dist, hub_height, lidar_height_offset):
    """ Windfield Description

    Computes the windfield description for the lower and upper planes.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing the LiDAR measurements

        Required columns:
        - :code:`los_id` - Line-of-sight
        - :code:`radial_windspeed` - Measured radial windspeed
        - :code:`pitch` - Pitch
        - :code:`roll` - Roll
        - :code:`status` - Status
    dist : float
        The distance of the measurements
    hub_height : float
        The height of the turbine
    lidar_height_offset : float, optional
        The height at which the lidar measures, relative to hub_height

    Returns
    -------
    pandas.DataFrame
        Columns:
        - :code:`shear`
        - :code:`veer`
        - :code:`status_upr`
        - :code:`status_lwr`
        - :code:`speed_upr`
        - :code:`speed_lwr`
        - :code:`dir_upr`
        - :code:`dir_lwr`
        - :code:`x_upr`
        - :code:`y_upr`
        - :code:`x_lwr`
        - :code:`y_lwr`
        - :code:`height_upr`
        - :code:`height_lwr`
    """

    if set(columns) - set(df.columns):
        raise ValueError('DataFrame columns must be {}'.format(columns))

    wfi = core.core_windfield_desc(
        df.index.values.astype(np.uint64),
        df.los_id.values.astype(np.int64),
        df.radial_windspeed.values,
        df.pitch.values,
        df.roll.values,
        df.status.values,
        dist,
        hub_height + lidar_height_offset,
        azimuths,
        zeniths
    )

    idx = pd.to_datetime(wfi['time'], utc=True, unit='ns')
    del wfi['time']
    return pd.DataFrame(wfi, index=idx)
