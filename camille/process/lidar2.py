from math import acos, atan2, cos, sin, tan, radians
import pandas as pd
from .lidar2extension import *

# Process

columns = ('los_id', 'radial_windspeed', 'status', 'pitch', 'roll')

def process(
        df,
        dist,
        hub_hgt=98.6,
        lidar_hgt=4.5,
        pitch_offset=radians(-2.0),
        roll_offset=radians(0.4),
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
    extra_columns : list of str, optional
        Export extra data. Sometimes it can be useful to export intermediate
        values computed by this processor. Available extra columns are:

        - :code:`shear` - Shear
        - :code:`veer` - Veer
        - :code:`rws[0-3]` - radial wind speeds
        - :code:`beam_hgt[0-3]` - beam heights
        - :code:`planar_ws_(upr|lwr)` - planar wind speeds
        - :code:`time[0-3]` - los sample times

    Returns
    -------
    pandas.DataFrame
        hws and hwd column contains the computed horizontal wind speeds and
        directions respectively
    """

    elevation = list(map(radians, [5.0, 5.0, -5.0, -5.0]))
    telescope = list(map(radians, [-15.0, 15.0, -15.0, 15.0]))
    zeniths  = [acos(cos(e) * cos(t)) for e, t in zip(elevation, telescope)]
    azimuths = [atan2(sin(e), tan(t)) for e, t in zip(elevation, telescope)]

    if set(df.columns) < set(columns):
        raise ValueError('DataFrame columns must be {}'.format(columns))

    out_columns = ['hws', 'hwd']
    if extra_columns is not None:
        out_columns += list(extra_columns)

    df = df.copy()

    # Ensure that unit is nanoseconds. This is assumed in C++ extension.
    df.index.astype('datetime64[ns]')

    df.index.name = 'time'
    df.los_id = df.los_id.astype('int')
    df.pitch += pitch_offset
    df.roll += roll_offset

    hws, hwd, shear, veer, ws_upper, ws_lower = ps(df.index, df.los_id,
                                                   df.pitch, df.roll,
                                                   df.radial_windspeed,
                                                   df.status, dist, hub_hgt,
                                                   lidar_hgt, azimuths, zeniths)
    out = pd.DataFrame({'hws': hws,
                        'hwd': hwd,
                        'shear': shear,
                        'veer': veer,
                        'ws_upper': ws_upper,
                        'ws_lower': ws_lower},
                       index=df.index)
    return out.dropna()
