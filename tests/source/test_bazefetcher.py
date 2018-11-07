#!/usr/bin/env python3
from camille.source import bazefetcher
from datetime import datetime, timedelta
from math import pi
from pytz import utc
import numpy as np
import pandas as pd
import pytest


authored = bazefetcher('tests/test_data/authored')
baze = bazefetcher('tests/test_data/baze')

t12_31_22 = datetime(2029, 12, 31, 22, tzinfo=utc)
t12_31_23 = datetime(2029, 12, 31, 23, tzinfo=utc)
t1_1 = datetime(2030, 1, 1, tzinfo=utc)
t1_1_1 = datetime(2030, 1, 1, 1, tzinfo=utc)
t1_3 = datetime(2030, 1, 3, tzinfo=utc)
t1_3_15 = datetime(2030, 1, 3, 15, tzinfo=utc)
t1_3_21 = datetime(2030, 1, 3, 21, tzinfo=utc)
t1_4_3 = datetime(2030, 1, 4, 3, tzinfo=utc)
t1_4_23 = datetime(2030, 1, 4, 23, tzinfo=utc)
t1_5 = datetime(2030, 1, 5, tzinfo=utc)
t1_5_1 = datetime(2030, 1, 5, 1, tzinfo=utc)

trng = pd.date_range(t1_1, t1_5, freq="S", name='time', closed='left')
t = trng.map(lambda t: (t - t1_1).total_seconds())

_sin = pd.Series(np.sin(t * pi / 60), index=trng, name='value')
_cos = pd.Series(np.cos(t * pi / 60), index=trng, name='value')
_tan = pd.Series(np.tan(t * pi / 60), index=trng, name='value')
def sin(t0=t1_1, tn=t1_5):
    eps = timedelta(microseconds=1)
    return _sin[t0:tn - eps]
def cos(t0=t1_1, tn=t1_5):
    eps = timedelta(microseconds=1)
    return _cos[t0:tn - eps]
def tan(t0=t1_1, tn=t1_5):
    eps = timedelta(microseconds=1)
    return _tan[t0:tn - eps]

def assert_correct(v, func, t0, t1):
    pd.testing.assert_series_equal(v, func(t0, t1))
    assert v.index[0] == t0
    assert v.index[-1] < t1
    assert (t1 - v.index[-1]).to_pytimedelta() < timedelta(seconds=2)

def test_read_two_days():
    sin_b = baze('Sin-T60s-SR1hz', t1_1, t1_3)
    tan_b = baze('Tan-T60s-SR1hz', t1_1, t1_3)
    assert len(sin_b) == len(tan_b) == 172800 # 2 days
    pd.testing.assert_series_equal(sin_b, sin(t1_1, t1_3))
    pd.testing.assert_series_equal(tan_b, tan(t1_1, t1_3))
    assert sin_b.index[0] == t1_1
    assert sin_b.index[-1] < t1_3
    assert (t1_3 - sin_b.index[-1]).to_pytimedelta() < timedelta(seconds=2)

def test_read_partially_before():
    cos_b = baze('Cos-T60s-SR1hz', t12_31_23, t1_1_1)
    assert len(cos_b) == 3600 # 1 hour
    assert_correct(cos_b, cos, t1_1, t1_1_1)

def test_read_partially_after():
    cos_b = baze('Cos-T60s-SR1hz', t1_4_23, t1_5_1)
    assert len(cos_b) == 3600 # 1 hour
    assert_correct(cos_b, cos, t1_4_23, t1_5)

def test_read_immersed():
    sin_b = baze('Sin-T60s-SR1hz', t1_3_15, t1_3_21)
    assert len(sin_b) == 21600 # 6 hours
    assert_correct(sin_b, sin, t1_3_15, t1_3_21)

def test_read_intersecting():
    tan_b = baze('Tan-T60s-SR1hz', t1_3_21, t1_4_3)
    assert len(tan_b) == 21600 # 6 hours
    assert_correct(tan_b, tan, t1_3_21, t1_4_3)

def test_read_covering_authored():
    i = pd.DatetimeIndex([
        t1_1,
        datetime(2030, 1, 2, tzinfo=utc),
        datetime(2030, 1, 2, 22, tzinfo=utc),
        datetime(2030, 1, 2, 23, 30, 30, tzinfo=utc),
        datetime(2030, 1, 3, tzinfo=utc),
    ], name='time')
    i04_status = pd.Series([1, 0, 1, 0, 1], index=i, name='value')
    i04_status_b = authored('installation-04-status', t12_31_23, t1_5_1)
    pd.testing.assert_series_equal(i04_status, i04_status_b)

def test_read_empty_tag():
    with pytest.raises(ValueError) as excinfo:
        authored('Empty-Tag', t1_1, t1_5)
    assert ('No data for {} between {} and {}'
        .format('Empty-Tag', t1_1, t1_5)
        in str(excinfo.value))

def test_read_outside():
    with pytest.raises(ValueError) as excinfo:
        baze('Cos-T60s-SR1hz', t12_31_22, t12_31_23)
    assert ('No data for {} between {} and {}'
        .format('Cos-T60s-SR1hz', t12_31_22, t12_31_23)
        in str(excinfo.value))

def test_non_existing_tag():
    with pytest.raises(ValueError) as excinfo:
        baze('non-existing-tag', t1_1, t1_1_1)
    assert 'Tag non-existing-tag not found' in str(excinfo.value)

def test_no_time_zone():
    t1_3_notz = datetime(2030, 1, 3)
    with pytest.raises(ValueError) as excinfo0: baze('Perlin', t1_3_notz, t1_5)
    with pytest.raises(ValueError) as excinfo1: baze('Perlin', t1_1, t1_3_notz)
    assert 'dates must be timezone aware' in str(excinfo0.value)
    assert 'dates must be timezone aware' in str(excinfo1.value)
