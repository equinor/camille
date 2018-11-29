#!/usr/bin/env python
from datetime import datetime
from math import radians
from os import path
from random import choice
import camille
import gzip
import pandas as pd
import pytest
import pytz
import shutil


min_date = datetime(2030, 1, 1, tzinfo=pytz.utc)
max_date = datetime(2030, 1, 4, tzinfo=pytz.utc)
date_range = pd.date_range(min_date, max_date, freq='30T', closed='left')
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

    cin = camille.source.bazefetcher('tests/test_data/processed')
    ref = cin('inst1-horiz-windspeed-{}m'.format(dist), start_date, end_date)[1:-1]

    wiris = camille.source.windiris(windiris_root)
    df = wiris(start_date, end_date, 'inst1').set_index('Timestamp')
    df.index.name = 'time'
    df.rename(columns={
            'LOS Index': 'los_id',
            'Distance': 'distance',
            'RWS': 'radial_windspeed',
            'RWS Status': 'status',
            'Tilt': 'pitch',
            'Roll': 'roll',
        }, inplace=True)
    df.pitch = df.pitch.apply(radians)
    df.roll = df.roll.apply(radians)
    g = df.groupby('distance')

    hws = camille.process.lidar(g.get_group(dist), dist)

    pd.testing.assert_series_equal(hws, ref)
