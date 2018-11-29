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


def horiz_windspeed(los, dist, hub_hgt, lidar_hgt, azimuths, zeniths):
    sensors = los.index.tolist()
    pitch_upr = (los.loc[0].pitch + los.loc[1].pitch) / 2.0
    pitch_lwr = (los.loc[2].pitch + los.loc[3].pitch) / 2.0
    roll_upr = (los.loc[0].roll + los.loc[1].roll) / 2.0
    roll_lwr = (los.loc[2].roll + los.loc[3].roll) / 2.0

    beam_hgts = [
        sample_hgt(s, hub_hgt, lidar_hgt, dist,
                   los.loc[s].pitch, los.loc[s].roll, azimuths[s], zeniths[s])
        for s in sensors
    ]
    hgt_upr = (beam_hgts[0] + beam_hgts[1]) * 0.5
    hgt_lwr = (beam_hgts[2] + beam_hgts[3]) * 0.5

    rws = [los.loc[s].radial_windspeed for s in sensors]
    ws_upr = planar_windspeed(
        rws[0], rws[1], pitch_upr, roll_upr, azimuths[0], zeniths[0])
    ws_lwr = planar_windspeed(
        rws[2], rws[3], pitch_lwr, roll_lwr, azimuths[2], zeniths[2])

    shear_coeff = shear_coefficient(ws_upr, ws_lwr, hgt_upr, hgt_lwr)
    return extrapolate_windspeed(hub_hgt, shear_coeff, ws_lwr, hgt_lwr)


# Predicates

def ordered_los_id_4(df): return df.los_id.tolist() == [0,1,2,3]
def los_id_4(df): return set(df.los_id) == set([0,1,2,3])
def all_ok(df): return (df.status == 1).all()
def max_duration(df, max_seconds=5.0):
    duration = df.index.max().to_pydatetime() - df.index.min().to_pydatetime()
    return duration.total_seconds() < max_seconds


def default_predicate(df):
    return ordered_los_id_4(df) and all_ok(df) and max_duration(df, 5.0)


# Process

columns = ('los_id', 'radial_windspeed', 'status', 'pitch', 'roll')

def process(df, dist,
        azimuths=None,
        zeniths=None,
        hub_hgt=98.6,
        lidar_hgt=4.5,
        pitch_offset=radians(-2.0),
        roll_offset=radians(0.4),
        predicate=default_predicate):

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

    for i, k in zip(range(len(df)), range(4, len(df))):
        win = df.iloc[i:k]
        time = win.index[0]
        if not predicate(win):
            hws.loc[time] = np.nan
            continue
        win = win.set_index('los_id').sort_index()
        hws0 = horiz_windspeed(win, dist, hub_hgt, lidar_hgt, azimuths, zeniths)
        hws.loc[time] = hws0

    return hws.dropna()
