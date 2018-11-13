from math import cos, sin, log, sqrt, radians
import typing

import pandas as pd
import numpy as np

Sample = typing.NewType('Sample', int)

__defaults = {
    'sample_dist': [50, 80, 120, 160, 200, 240, 280, 320, 360, 400],
    'zeniths': list(map(radians, [15.79, 15.79, 15.79, 15.79])),
    'azimuths': list(map(radians, [18.0181, 161.9819, -18.0181, -161.9819])),
    'hub_hight': 98.6,
    'lidar_height': 4.5,
    'pitch_offset': radians(-2.0),
    'roll_offset': radians(0.4),
}


def process(df, **kwargs):
    options = ('sample_dist', 'zeniths', 'azimuths', 'hub_height',
               'lidar_height', 'rotor_distance', 'pitch_offset', 'roll_offset')
    if not all([key in options for key in kwargs.keys()]):
        raise ValueError(
            'Unknown argument(s) {}'.format(kwargs.keys() - options))

    columns = ('timestamp', 'los_id', 'distance', 'radial_windspeed', 'status',
               'pitch', 'roll')
    if set(df.columns) != set(columns):
        raise ValueError('DataFrame columns must be {}'.format(columns))

    sample_dist = kwargs.get('sample_dist', __defaults['sample_dist'])
    zeniths = kwargs.get('zeniths', __defaults['zeniths'])
    azimuths = kwargs.get('azimuths', __defaults['azimuths'])
    hub_hight = kwargs.get('hub_hight', __defaults['hub_hight'])
    lidar_height = kwargs.get('lidar_height', __defaults['lidar_height'])
    pitch_offset = kwargs.get('pitch_offset', __defaults['pitch_offset'])
    roll_offset = kwargs.get('roll_offset', __defaults['roll_offset'])

    sensors = list(range(4))

    def group(df):
        """The lidar data is layed out such that one sample cycle is 40 rows
        long. One sample cycle contains 4 samples, one each second. Each sample
        is 10 rows. Our calculations require that the 4 samples, of ids 0, 1, 2,
        and 3, in each sample cycle are consecutive. In the input data this is
        however not always the caseself.

        This function groups sample cycles that consecutively contain all 40
        samples in the order 0 -> 1 -> 2 -> 3. Any other samples are discarded.
        """
        g = df.copy()
        g.distance = g.distance.apply(int)

        pattern = [0] * 10 + [1] * 10 + [2] * 10 + [3] * 10
        i = 0
        group = 0
        groups = []
        while i < len(g):
            if (i + 39 < len(g) and
                    g.iloc[i:i + 40].los_id.tolist() == pattern):
                groups += [group] * 40
                i += 40
                group += 1
            else:
                groups += [-1]
                i += 1

        g['group'] = groups

        g = g[g.group != -1]
        g = g.set_index(['group', 'distance', 'los_id']).sort_index()
        return g

    grouped = group(df)
    group_count = grouped.index.get_level_values('group').max() + 1

    def sample_timestamp(s: Sample):
        return grouped.loc[s].timestamp.min()

    def radial_windspeed(s: Sample, los_id, distance):
        return grouped.loc[s, distance, los_id].radial_windspeed

    def los_status(s):
        return all(grouped.loc[s].status)

    def sample_pitch(s: Sample, los_id):
        return grouped.loc[s, sample_dist[0], los_id].pitch + pitch_offset

    def sample_roll(s: Sample, los_id):
        return grouped.loc[s, sample_dist[0], los_id].roll + roll_offset

    def sample_height(i, distance, pitch, roll, azimuth, zenith):
        sign = -1 if i >= 2 else 1
        return hub_hight + lidar_height + distance * (
            cos(zenith) * sin(pitch) +
            sign * sin(zenith) * cos(azimuth) * cos(pitch) * sin(roll) +
                   sin(zenith) * sin(azimuth) * cos(pitch) * cos(roll))

    def planar_windspeed(rws_a, rws_b, pitch, roll, azimuth, zenith):
        x_divisor = 2 * (cos(zenith) * cos(pitch) +
                         sin(zenith) * cos(azimuth) * sin(pitch) * sin(roll) -
                         sin(zenith) * sin(azimuth) * sin(pitch) * cos(roll))
        x = (rws_a + rws_b) / x_divisor
        y = (rws_a - rws_b) / (2 * sin(zenith) * cos(azimuth) * cos(roll))
        return sqrt(x ** 2 + y ** 2)

    def horizontal_windspeed(s: Sample, distance):
        pitch_upper = (sample_pitch(s, 0) + sample_pitch(s, 1)) * 0.5
        pitch_lower = (sample_pitch(s, 2) + sample_pitch(s, 3)) * 0.5
        roll_upper = (sample_roll(s, 0) + sample_roll(s, 1)) * 0.5
        roll_lower = (sample_roll(s, 2) + sample_roll(s, 3)) * 0.5

        heights = [
            sample_height(i, distance, sample_pitch(s, i), sample_roll(s, i),
                          azimuths[i], zeniths[i]) for i in sensors
        ]

        rws = [radial_windspeed(s, i, distance) for i in sensors]
        pws0 = planar_windspeed(rws[0], rws[1], pitch_upper, roll_upper, azimuths[0], zeniths[0])
        pws1 = planar_windspeed(rws[2], rws[3], pitch_lower, roll_lower, azimuths[2], zeniths[2])

        plane_height_upper = (heights[0] + heights[1]) * 0.5
        plane_height_lower = (heights[2] + heights[3]) * 0.5

        alpha = log(pws0 / pws1) / log(plane_height_upper / plane_height_lower)
        hws = pws1 * pow(hub_hight / plane_height_lower, alpha)

        return hws

    out = pd.DataFrame(index=list(range(group_count)))
    out['timestamp'] = out.index.map(sample_timestamp)
    for d in sample_dist:
        out['hws{}'.format(d)] = out.index.map(lambda s: horizontal_windspeed(s, d))
    return out
