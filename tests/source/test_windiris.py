#!/usr/bin/env python3
from camille.source import windiris
from datetime import datetime
from pytz import timezone, utc
import pytest

wi = windiris('tests/test_data/windiris')

def test_load_all_data():
    s = datetime(2017, 12, 17, tzinfo=utc)
    e = datetime(2018, 10, 23, tzinfo=utc)

    df = wi('inst2', s, e)

    assert df.shape[0] == 27
    assert (
                df.radial_windspeed == [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                         2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
                                         3, 3, 3, 3, 3, 3 ]
           ).all()


def test_load_one_day():
    s = datetime(2017, 12, 17, tzinfo=utc)
    e = datetime(2017, 12, 18, tzinfo=utc)

    df = wi('inst2', s, e)

    assert df.shape[0] == 11
    assert (
                df.radial_windspeed == [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ]
           ).all()

    s = datetime(2017, 12, 18, tzinfo=utc)
    e = datetime(2017, 12, 19, tzinfo=utc)

    df = wi('inst2', s, e)

    assert df.shape[0] == 10
    assert (
                df.radial_windspeed == [ 2, 2, 2, 2, 2, 2, 2, 2, 2, 2 ]
           ).all()

def test_left_closed():
    s = datetime(2018, 10, 22, 8, 30, 0, 603438, tzinfo=utc)
    e = datetime(2018, 10, 23, tzinfo=utc)

    df = wi('inst2', s, e)

    assert df.shape[0] == 6
    assert (
                df.radial_windspeed == [ 3, 3, 3, 3, 3, 3 ]
           ).all()

def test_right_open():
    s = datetime(2017, 12, 17, tzinfo=utc)
    e = datetime(2017, 12, 18, 16,30, 0, 603437, tzinfo=utc)

    df = wi('inst2', s, e)

    assert df.shape[0] == 11
    assert (
                df.radial_windspeed == [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ]
           ).all()

def test_filter():
    s = datetime(2017, 12, 17, tzinfo=utc)
    e = datetime(2018, 10, 23, tzinfo=utc)

    df = wi('inst2', s, e, los_id=0)

    assert df.shape[0] == 3
    assert (
                df.radial_windspeed == [ 1, 2, 3 ]
           ).all()

    df = wi('inst2', s, e, los_id=[0, 1])

    assert df.shape[0] == 6
    assert (
                df.radial_windspeed == [ 1, 1, 2, 2, 3, 3 ]
           ).all()

    df = wi('inst2', s, e, distance=1)

    assert df.shape[0] == 3
    assert (
                df.radial_windspeed == [ 1, 2, 3 ]
           ).all()

    df = wi('inst2', s, e, distance=[1,2])

    assert df.shape[0] == 6
    assert (
                df.radial_windspeed == [ 1, 1, 2, 2, 3, 3 ]
           ).all()

    df = wi('inst2', s, e, status=0)

    assert df.empty

def test_timezone():
    dates_tzinfo = timezone("Australia/Melbourne")
    s = datetime(2017, 12, 19)
    s = dates_tzinfo.localize(s)
    e = datetime(2017, 12, 20)
    e = dates_tzinfo.localize(e)

    data_tzinfo = timezone("Asia/Calcutta")
    wi = windiris('tests/test_data/windiris', data_tzinfo)
    df = wi('inst2', s, e)

    assert df.shape[0] == 10
    assert (
                df.radial_windspeed == [ 2, 2, 2, 2, 2, 2, 2, 2, 2, 2 ]
           ).all()

    assert df.index.tz == data_tzinfo

def test_not_directory():
    with pytest.raises(ValueError) as exc:
        windiris('tests/test_data/windiris/inst1/inst1_rtd.db.gz')
    assert ('not a directory' in str(exc.value))

def test_installation_not_found():
    date = datetime(2017, 1, 1, tzinfo=utc)
    with pytest.raises(ValueError) as exc:
        wi('non_existent_installation', date, date)
    assert 'not found' in str(exc)

def test_no_time_zone():
    tz_date = datetime(2017, 1, 1, tzinfo=utc)
    ntz_date = datetime(2017, 1, 1)
    with pytest.raises(ValueError) as exc:
        wi('inst2', tz_date, ntz_date)
    assert 'timezone aware' in str(exc)

    with pytest.raises(ValueError) as exc:
        wi('inst2', ntz_date, tz_date)
    assert 'timezone aware' in str(exc)
