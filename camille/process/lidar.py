from math import cos, sin, log, sqrt, radians

import pandas as pd
import numpy as np

defaults = {
    'zeniths': list(map(radians, [15.79, 15.79, 15.79, 15.79])),
    'azimuths': list(map(radians, [18.0181, 161.9819, -18.0181, -161.9819])),
    'hub_hgt': 98.6,
    'lidar_hgt': 4.5,
    'pitch_offset': radians(-2.0),
    'roll_offset': radians(0.4),
}

options = ('zeniths', 'azimuths', 'hub_hgt', 'lidar_hgt', 'rotor_dist',
           'pitch_offset', 'roll_offset')

columns = ('timestamp', 'los_id', 'dist', 'radial_windspeed', 'status',
           'pitch', 'roll')


def sample_hgt(i, dist, pitch, roll, azm, zn):
    sign = -1 if i >= 2 else 1
    return hub_hgt + lidar_hgt + dist * (
        cos(zn) * sin(pitch) +
        sign * sin(zn) * cos(azm) * cos(pitch) * sin(roll) +
               sin(zn) * sin(azm) * cos(pitch) * cos(roll))


def planar_windspeed(rws_a, rws_b, pitch, roll, azm, zn):
    x_divisor = 2 * (cos(zn) * cos(pitch) +
                     sin(zn) * cos(azm) * sin(pitch) * sin(roll) -
                     sin(zn) * sin(azm) * sin(pitch) * cos(roll))
    x = (rws_a + rws_b) / x_divisor
    y = (rws_a - rws_b) / (2 * sin(zn) * cos(azm) * cos(roll))
    return sqrt(x ** 2 + y ** 2)


def shear_coefficient(pws_upr, pws_lwr, hgt_upr, hgt_lwr):
    return log(pws_upr / pws_lwr) / log(hgt_upr / hgt_lwr)


def horiz_windspeed(hgt, shear_coeff, ref_windspeed, ref_hgt):
    return ref_windspeed * pow(hgt / ref_hgt, shear_coeff)


def process(df, **kwargs):
    if not all([key in options for key in kwargs.keys()]):
        diff = kwargs.keys() - options
        raise ValueError('Unknown argument(s) {}'.format(diff))
    if set(df.columns) != set(columns):
        raise ValueError('DataFrame columns must be {}'.format(columns))

    zeniths = kwargs.get('zeniths', defaults['zeniths'])
    azimuths = kwargs.get('azimuths', defaults['azimuths'])
    hub_hgt = kwargs.get('hub_hgt', defaults['hub_hgt'])
    lidar_hgt = kwargs.get('lidar_hgt', defaults['lidar_hgt'])
    pitch_offset = kwargs.get('pitch_offset', defaults['pitch_offset'])
    roll_offset = kwargs.get('roll_offset', defaults['roll_offset'])

    sensors = list(range(4))

    for i, k in zip(range(len(df)), range(4, len(df))):
        ...
