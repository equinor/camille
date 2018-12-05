#!/usr/bin/env python3
from camille.source import bazefetcher
from camille.util import baze_iterator
from camille.util.baze_iterator import _check_time
from camille.util.baze_iterator import _check_timedelta
from datetime import datetime, timedelta
from math import pi
from pytz import utc
import pytest
import pandas as pd
import numpy as np


baze = bazefetcher('tests/test_data/baze')
tag = 'Sin-T60s-SR01hz'

t1 = datetime(2030, 1, 1, tzinfo=utc)
t2 = datetime(2030, 1, 2, tzinfo=utc)
t3 = datetime(2030, 1, 3, tzinfo=utc)
t4 = datetime(2030, 1, 4, tzinfo=utc)

invalid_date = datetime(2030, 1, 1, 10, tzinfo=utc)
invalid_interval = timedelta(1.5)

trng = pd.date_range(t1, t4, freq="10S", name='time', closed='left')
t = trng.map(lambda t: (t - t1).total_seconds())

_sin = pd.Series(np.sin(t * pi / 6), index=trng, name='value')

def sin(t0=t1, tn=t4):
    eps = timedelta(microseconds=1)
    return _sin[t0:tn - eps]


def test_baze_iterator():
    for data, s, e in baze_iterator(baze, tag, t1, t2):
        assert len(data) == 8640
        pd.testing.assert_series_equal(data, sin(s, e))


def test_left_padding():
    padding = timedelta(hours=1)
    for data, s, e in baze_iterator(baze, tag, t2, t3, padding=padding):
        assert len(data) == 9000
        pd.testing.assert_series_equal(data, sin(s - padding, e))


def test_right_padding():
    padding = timedelta(hours=1)
    for data, s, e in baze_iterator(baze, tag, t2, t3, padding=padding, leftpad=False, rightpad=True):
        assert len(data) == 9000
        pd.testing.assert_series_equal(data, sin(s, e + padding))


def test_time_check():
    with pytest.raises(ValueError):
        _check_time(invalid_date)


def test_timedelta_check():
    with pytest.raises(ValueError):
        _check_timedelta(invalid_interval)
