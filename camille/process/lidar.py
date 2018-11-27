from math import cos, sin, log, sqrt, radians
from datetime import timedelta

import pandas as pd
import numpy as np


def sample_hgt(i, hub_hgt, lidar_hgt, dist, pitch, roll, azm, zn):
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


def shear_coefficient(ws_upr, ws_lwr, hgt_upr, hgt_lwr):
    return log(ws_upr / ws_lwr) / log(hgt_upr / hgt_lwr)


def extrapolate_windspeed(hgt, shear_coeff, ref_windspeed, ref_hgt):
    return ref_windspeed * pow(hgt / ref_hgt, shear_coeff)


def horiz_windspeed(df, dist, hub_hgt, lidar_hgt, azimuths, zeniths):
    sensors = df.index.tolist()
    pitch_upr = (df[0].pitch + df[1].pitch) / 2.0
    pitch_lwr = (df[2].pitch + df[3].pitch) / 2.0
    roll_upr = (df[0].roll + df[1].roll) / 2.0
    roll_lwr = (df[2].roll + df[3].roll) / 2.0

    beam_hgts = [
        sample_hgt(s, hub_hgt, lidar_hgt, dist,
                   df[s].pitch, df[s].roll, azimuths[s], zeniths[s])
        for s in sensors
    ]
    hgt_upr = (hgts[0] + hgts[1]) * 0.5
    hgt_lwr = (hgts[2] + hgts[3]) * 0.5

    rws = [df[s].radial_windspeed for s in sensors]
    ws_upr = planar_windspeed(
        rws[0], rws[1], pitch_upr, roll_upr, azimuths[0], zeniths[0])
    ws_lwr = planar_windspeed(
        rws[2], rws[3], pitch_lwr, roll_lwr, azimuths[2], zeniths[2])

    shear_coeff = shear_coefficient(ws_upr, ws_lwr, hgt_upr, hgt_lwr)
    return extrapolate_windspeed(hub_hgt, shear_coeff, ws_lwr, plane_hgt_lwr)


# Predicates

def ordered_los_id_4(df): return df.los_id.tolist() == [0,1,2,3]
def los_id_4(df): return set(df.los_id) == set([0,1,2,3])
def all_ok(df): return (df.status == 1).all()
def max_duration(df, max_seconds=5.0):
    duration = df.time.max().to_pydatetime() - df.time.min().to_pydatetime()
    return duration.total_seconds() < max_seconds


def default_predicate(df):
    return ordered_los_id_4(df) and all_ok(df) and max_duration(df, 5.0)


# Process

columns = ('time', 'los_id', 'radial_windspeed', 'status', 'pitch', 'roll')

def process(df, dist,
        azimuths=list(map(radians, [18.0181, 161.9819, -18.0181, -161.9819])),
        zeniths=list(map(radians, [15.79, 15.79, 15.79, 15.79])),
        hub_hgt=98.6,
        lidar_hgt=4.5,
        pitch_offset=radians(-2.0),
        roll_offset=radians(0.4),
        predicate=default_predicate):

    if set(df.columns) != set(columns):
        raise ValueError('DataFrame columns must be {}'.format(columns))

    df = df.copy()
    df.pitch += pitch_offset
    df.roll += roll_offset

    hws = pd.Series(index=pd.DatetimeIndex())

    for i, k in zip(range(len(df)), range(4, len(df))):
        win = df.iloc[i, k]
        time = win.iloc[0].time
        if not pred(win):
            hws.loc[time] = np.nan
            continue
        hws0 = horiz_windspeed(win, dist, hub_hgt, lidar_hgt, azimuths, zeniths)
        hws.loc[time] = hws0

    return hws
