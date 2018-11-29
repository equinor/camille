#!/usr/bin/env python
from datetime import datetime
from math import radians
from os import path
import camille
import gzip
import pandas as pd
import pytest
import pytz
import shutil



@pytest.fixture(autouse=True)
def windiris_root(tmpdir):
    tmpdir.mkdir('windiris').mkdir('inst1')
    compressed_db_path = 'tests/test_data/windiris/inst1/inst1_rtd.db.gz'
    db_path = tmpdir.join('windiris/inst1/inst1_rtd.db')
    with gzip.open(compressed_db_path, 'rb') as fin:
        with open(str(db_path), 'wb') as fout:
            shutil.copyfileobj(fin, fout)

    windiris_root = str(tmpdir.join('windiris'))
    yield windiris_root

def test_lidar(windiris_root):
    start_date = datetime(2030, 1, 1, tzinfo=pytz.utc)
    end_date = datetime(2030, 1, 1, 0, 15, tzinfo=pytz.utc)

    cin = camille.source.bazefetcher('tests/test_data/processed')
    ref = cin('inst1-horiz-windspeed-50m', start_date, end_date)

    wiris = camille.source.windiris(windiris_root)
    df = wiris('inst1', 50, start_date, end_date)

    hws = camille.process.lidar(g.get_group(50), 50)

    pd.testing.assert_series_equal(hws, ref)
