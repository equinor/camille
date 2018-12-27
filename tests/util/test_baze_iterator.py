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
#sin data are spaced per every 10 seconds
day_data_length = 24 * 60 * 6

def sin(t0=t1, tn=t4):
    eps = timedelta(microseconds=1)
    return _sin[t0:tn - eps]


def test_baze_iterator():
    for ind, (data, s, e) in enumerate(baze_iterator(baze, tag, t1, t2)):
        assert s == t1
        assert e == t2
        assert len(data) == 8640
        pd.testing.assert_series_equal(data, sin(s, e))
    assert  ind == 0


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


def test_same_date():
    with pytest.raises(StopIteration):
        next(baze_iterator(baze, tag, t3, t3, timedelta(1)))


def test_non_one_day_interval():
    for ind, (data, s, e) in enumerate(baze_iterator(baze, tag, t1, t4, timedelta(3))):
        assert s == t1
        assert e == t4
        assert len(data) == day_data_length * 3
    assert ind == 0


def test_interval_bigger_than_range():
    for ind, (data, s, e) in enumerate(baze_iterator(baze, tag, t1, t2, timedelta(5))):
        assert s == t1
        assert e == t2
        assert len(data) == day_data_length
    assert ind == 0


def test_interval_not_fitting_range():
    exp_days = [2, 1]
    s_dates = [t1, t3]
    e_dates = [t3, t4]
    for ind, (data, s, e) in enumerate(baze_iterator(baze, tag, t1, t4, timedelta(2))):
        assert  s == s_dates[ind]
        assert  e == e_dates[ind]
        assert len(data) == day_data_length * exp_days[ind]
    assert  ind == 1
