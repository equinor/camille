#!/usr/bin/env python
from datetime import datetime
from math import radians
from random import choice
import camille
import gzip
import pandas as pd
import pytest
import pytz
import shutil


min_date = datetime(2030, 1, 1, tzinfo=pytz.utc)
max_date = datetime(2030, 1, 4, tzinfo=pytz.utc)
date_range = pd.date_range(min_date, max_date, freq='15T', closed='left')
distances = [50, 80, 120, 160, 200, 240, 280, 320, 360, 400]


@pytest.fixture(scope='module')
def windiris_root(tmpdir_factory):
    tmpdir = tmpdir_factory.mktemp('windiris')
    tmpdir.mkdir('inst1')
    compressed_db_path = 'tests/test_data/windiris/inst1/inst1_rtd.db.gz'
    db_path = str(tmpdir.join('inst1/inst1_rtd.db'))
    with gzip.open(compressed_db_path, 'rb') as fin:
        with open(db_path, 'wb') as fout:
            shutil.copyfileobj(fin, fout)

    windiris_root = str(tmpdir)
    yield windiris_root


@pytest.mark.repeat(5)
def test_lidar(windiris_root):
    dist = choice(distances)
    start_date, end_date = choice(list(zip(date_range[:-1], date_range[1:])))
    print("Parameters: dist={}, start_date={}, end_date={}"
        .format(dist, start_date, end_date))

    cin = camille.source.Bazefetcher('tests/test_data/processed')
    ref = cin('inst1-horiz-windspeed-{}m'.format(dist), start_date, end_date)

    wiris = camille.source.windiris(windiris_root)
    df = wiris('inst1', start_date, end_date, distance=dist)

    hws = camille.process.lidar(df, dist).hws

    pd.testing.assert_series_equal(hws, ref, check_names=False)


def test_lidar_extra_columns_share_coeff(windiris_root):
    dist = 120
    start = datetime(2030, 1, 1, tzinfo=pytz.utc)
    end = datetime(2030, 1, 1, 0, 5, tzinfo=pytz.utc)
    extra_columns = ['shear_coeff']

    cin = camille.source.Bazefetcher('tests/test_data/processed')
    ref = pd.DataFrame({
        'hws': cin('inst1-horiz-windspeed-{}m'.format(dist), start, end),
        'shear_coeff': cin('inst1-shear-coeff-{}m'.format(dist), start, end),
    }, columns=['hws'] + extra_columns)

    wiris = camille.source.windiris(windiris_root)
    li = wiris('inst1', start, end, distance=dist)

    p = camille.process.lidar(li, dist, extra_columns=extra_columns)

    pd.testing.assert_frame_equal(p, ref)



def test_lidar_all_extra_columns(windiris_root):
    dist = 50
    start = datetime(2030, 1, 1, tzinfo=pytz.utc)
    end = datetime(2030, 1, 1, 0, 5, tzinfo=pytz.utc)
    extra_columns = [
        'shear_coeff',
        'rws0', 'rws1', 'rws2', 'rws3',
        'beam_hgt0', 'beam_hgt1', 'beam_hgt2', 'beam_hgt3',
        'planar_ws_upr', 'planar_ws_lwr',
        'time0', 'time1', 'time2', 'time3',
    ]

    cin = camille.source.Bazefetcher('tests/test_data/processed')
    ref = pd.DataFrame({
        'hws': cin('inst1-horiz-windspeed-{}m'.format(dist), start, end),
        **{
            c: cin('inst1-{}-{}m'.format(c.replace('_', '-'), dist), start, end)
            for c in extra_columns
        },
    }, columns=['hws'] + extra_columns)
    ref.time0 = pd.to_datetime(ref.time0, unit='ms', utc=True)
    ref.time1 = pd.to_datetime(ref.time1, unit='ms', utc=True)
    ref.time2 = pd.to_datetime(ref.time2, unit='ms', utc=True)
    ref.time3 = pd.to_datetime(ref.time3, unit='ms', utc=True)

    wiris = camille.source.windiris(windiris_root)
    li = wiris('inst1', start, end, distance=dist)

    p = camille.process.lidar(li, dist, extra_columns=extra_columns)
    p.time3 = pd.to_datetime(p.time3)
    p.time0 = pd.to_datetime(p.time0)
    p.time1 = pd.to_datetime(p.time1)
    p.time2 = pd.to_datetime(p.time2)

    pd.testing.assert_frame_equal(p, ref)
