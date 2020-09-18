#!/usr/bin/env python3
from camille.source import Bazefetcher, TagNotFoundError
from camille.source.bazefetcher import _get_files_between_start_and_end
from datetime import datetime, timedelta
from math import pi
from pytz import utc
import numpy as np
import pandas as pd
import pytest


authored = Bazefetcher('tests/test_data/authored')
baze = Bazefetcher('tests/test_data/baze')
non_standard = Bazefetcher('tests/test_data/non_standard_names')

t12_31_22 = datetime(2029, 12, 31, 22, tzinfo=utc)
t12_31_23 = datetime(2029, 12, 31, 23, tzinfo=utc)
t1_1 = datetime(2030, 1, 1, tzinfo=utc)
t1_2 = datetime(2030, 1, 2, tzinfo=utc)
t1_4 = datetime(2030, 1, 4, tzinfo=utc)
t1_1_1 = datetime(2030, 1, 1, 1, tzinfo=utc)
t1_3 = datetime(2030, 1, 3, tzinfo=utc)
t1_3_15 = datetime(2030, 1, 3, 15, tzinfo=utc)
t1_3_21 = datetime(2030, 1, 3, 21, tzinfo=utc)
t1_4_3 = datetime(2030, 1, 4, 3, tzinfo=utc)
t1_4_23 = datetime(2030, 1, 4, 23, tzinfo=utc)
t1_5 = datetime(2030, 1, 5, tzinfo=utc)
t1_5_1 = datetime(2030, 1, 5, 1, tzinfo=utc)

trng = pd.date_range(t1_1, t1_5, freq="10S", name='time', closed='left')
t = trng.map(lambda t: (t - t1_1).total_seconds())

_sin = pd.Series(np.sin(t * pi / 6), index=trng, name='value')
_cos = pd.Series(np.cos(t * pi / 6), index=trng, name='value')
_tan = pd.Series(np.tan(t * pi / 6), index=trng, name='value')
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
    assert (t1 - v.index[-1]).to_pytimedelta() < timedelta(seconds=20)

def test_read_two_days():
    sin_b = baze('Sin-T60s-SR01hz', t1_2, t1_4)
    tan_b = baze('Tan-T60s-SR01hz', t1_2, t1_4)
    assert len(sin_b) == len(tan_b) == 17280 # 2 days
    pd.testing.assert_series_equal(sin_b, sin(t1_2, t1_4))
    pd.testing.assert_series_equal(tan_b, tan(t1_2, t1_4))
    assert sin_b.index[0] == t1_2
    assert sin_b.index[-1] < t1_4
    assert (t1_4 - sin_b.index[-1]).to_pytimedelta() < timedelta(seconds=20)

def test_read_partially_before():
    cos_b = baze('Cos-T60s-SR01hz', t12_31_23, t1_1_1)
    assert len(cos_b) == 360 # 1 hour
    assert_correct(cos_b, cos, t1_1, t1_1_1)

def test_read_partially_after():
    cos_b = baze('Cos-T60s-SR01hz', t1_4_23, t1_5_1)
    assert len(cos_b) == 360 # 1 hour
    assert_correct(cos_b, cos, t1_4_23, t1_5)

def test_read_immersed():
    sin_b = baze('Sin-T60s-SR01hz', t1_3_15, t1_3_21)
    assert len(sin_b) == 2160 # 6 hours
    assert_correct(sin_b, sin, t1_3_15, t1_3_21)

def test_read_intersecting():
    tan_b = baze('Tan-T60s-SR01hz', t1_3_21, t1_4_3)
    assert len(tan_b) == 2160 # 6 hours
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
    empty_tag = authored('Empty-Tag', t1_1, t1_5)
    assert empty_tag.empty
    assert empty_tag.name == 'value'
    assert empty_tag.index.name == 'time'

def test_read_outside_timeseries_in_file():
    empty_time_series = baze('Cos-T60s-SR01hz', t12_31_22, t12_31_23)
    assert empty_time_series.empty
    assert empty_time_series.name == 'value'
    assert empty_time_series.index.name == 'time'

def test_no_directories():
    with pytest.raises(ValueError) as excinfo:
        Bazefetcher('tests/test_data/baze/perling')
    assert ('no file in [\'tests/test_data/baze/perling\'] is a directory'
            in str(excinfo.value))

def test_non_existing_tag():
    with pytest.raises(TagNotFoundError) as excinfo:
        baze('non-existing-tag', t1_1, t1_1_1)
    assert 'Tag non-existing-tag not found' in str(excinfo.value)

def test_no_time_zone():
    t1_3_notz = datetime(2030, 1, 3)
    with pytest.raises(ValueError) as excinfo0: baze('Perlin', t1_3_notz, t1_5)
    with pytest.raises(ValueError) as excinfo1: baze('Perlin', t1_1, t1_3_notz)
    assert 'dates must be timezone aware' in str(excinfo0.value)
    assert 'dates must be timezone aware' in str(excinfo1.value)

def test_snap_backward_within_file():
    inst4 = authored('installation-04-status',
                     t1_1_1,
                     t1_2,
                     snap='left')

    assert ( inst4.index == [ datetime(2030, 1, 1, tzinfo=utc) ] ).all()
    assert ( inst4 == [ 1 ] ).all()

snap_backward_outside_file_data = [(t1_5, t1_5_1), (t1_4, t1_4_3)]

@pytest.mark.parametrize("t0,t1", snap_backward_outside_file_data)
def test_snap_backward_outside_file(t0, t1):
    inst4 = authored('installation-04-status',
                     t0,
                     t1,
                     snap='left')

    assert ( inst4.index == [ datetime(2030, 1, 3, tzinfo=utc) ] ).all()
    assert ( inst4 == [ 1 ] ).all()

def test_snap_forward_within_file():
    t1_2_0_1 = t1_2 + timedelta(seconds=2)
    inst4 = authored('installation-04-status',
                     t1_2,
                     t1_2_0_1,
                     snap='right')
    ref_dates = [
        datetime(2030, 1, 2, 0, 0, tzinfo=utc),
        datetime(2030, 1, 2, 22, 0, tzinfo=utc)
    ]
    assert (inst4.index == ref_dates).all()
    assert (inst4 == [0, 1]).all()


snap_forward_outside_file_data = [(t12_31_22, t12_31_23), (t12_31_22, t1_1)]

@pytest.mark.parametrize("t0,t1", snap_forward_outside_file_data)
def test_snap_forward_outside_file(t0, t1):
    inst4 = authored('installation-04-status',
                     t0,
                     t1,
                     snap='right')

    assert ( inst4.index == [ datetime(2030, 1, 1, tzinfo=utc) ] ).all()
    assert ( inst4 == [ 1 ] ).all()

def test_snap_both():
    inst4 = authored('installation-04-status',
                     t1_2 + timedelta(seconds=1),
                     t1_2 + timedelta(seconds=2),
                     snap='both')
    ref_dates = [
        datetime(2030, 1, 2, 0, 0, tzinfo=utc),
        datetime(2030, 1, 2, 22, 0, tzinfo=utc)
    ]
    assert (inst4.index == ref_dates).all()
    assert (inst4 == [0, 1]).all()


def test_many_roots():
    baze_and_authored = Bazefetcher(
        ['tests/test_data/authored', 'tests/test_data/baze'])

    sin_b = baze_and_authored('Sin-T60s-SR01hz', t1_2, t1_4)
    assert len(sin_b) == 17280

    i04_status_b = authored('installation-04-status', t12_31_23, t1_5_1)
    assert len(i04_status_b) == 5


def test_many_roots_same_tag():
    roots = ['tests/test_data/many_roots/dir'+ str(index)
             for index in [3, 1, 2]]
    many_roots = Bazefetcher(roots)
    tag = "root_tag"
    root = many_roots(tag, t1_1, t1_5)
    assert len(root) == 7

    root = many_roots(tag, t1_3, t1_3_21)
    assert len(root) == 1

    root = many_roots(tag, t1_3, t1_3_21, snap='right')
    assert len(root) == 2


def test_many_roots_same_filename():
    roots = ['tests/test_data/many_roots/dir'+ str(index)
             for index in [1, 4]]
    many_roots = Bazefetcher(roots)
    with pytest.raises(ValueError) as excinfo:
        many_roots("root_tag", t1_1, t1_5)
    assert ('files [\'root_tag_2030-01-03T00.00.00+00.00_2030-01-04T00.00.00'
            '+00.00.json.gz\'] are not unique' in str(excinfo.value))


def test_no_time_boundaries():
    sin_b = baze('Sin-T60s-SR01hz')
    assert len(sin_b) == 34560 # 4 days
    pd.testing.assert_series_equal(sin_b, sin(t1_1, t1_5))
    assert sin_b.index[0] == t1_1
    assert sin_b.index[-1] < t1_5
    assert (t1_1 - sin_b.index[-1]).to_pytimedelta() < timedelta(seconds=20)


def test_no_unnecessary_files_read():
    #testing private method to cover the case where unnecessary files were readlllll
    files = _get_files_between_start_and_end(
        authored.src_dirs, 'installation-04-status', t1_2, t1_3)
    assert len(files) == 1


def test_load_tmp_file():
    sin_data = non_standard('tmp-file')
    sin_data_missing_day = non_standard('tmp-file', t1_2, t1_3)
    assert len(sin_data) == (6 * 60 * 24 * 3)  # 3 days
    assert len(sin_data_missing_day) == 0


def test_load_err_file():
    sin_data = non_standard('err-file')
    sin_data_missing_day = non_standard('err-file', t1_2, t1_3)
    assert len(sin_data) == (6 * 60 * 24 * 3)  # 3 days
    assert len(sin_data_missing_day) == 0


def test_load_special_regex_file():
    sin_data = non_standard('tag-with+plus-sign')
    assert len(sin_data) == 34560  # 4 days
    pd.testing.assert_series_equal(sin_data, sin(t1_1, t1_5))


def test_load_bad_format_file():
    df = baze('bad_format')
    assert df.empty
