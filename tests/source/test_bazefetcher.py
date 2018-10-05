#!/usr/bin/env python3
import datetime
import pytz
import pytest
from camille.source import bazefetcher


start_date = datetime.datetime(2018, 4, 9, tzinfo=pytz.utc)
end_date = datetime.datetime(2018, 5, 11, tzinfo=pytz.utc)
start_date_no_tz = datetime.datetime(2018, 4, 9)
future_date = datetime.datetime(2018, 6, 1, tzinfo=pytz.utc)
bazefield = bazefetcher('tests/test_data/bazefield_data_root')


def test_bazefetcher():
    tag2 = bazefield('installation-04-tag-2', start_date, end_date)
    assert len(tag2) == 576
    assert (1.100000e+32 < tag2).all()
    assert (tag2 < 1.300000e+32).all()
    assert min(tag2.index) >= start_date
    assert max(tag2.index) < end_date

    aaa = bazefield('AAA....  -.-  ...0000---__aa', start_date, end_date)
    assert min(aaa.index) >= start_date
    assert max(aaa.index) < end_date


def test_bad_input():
    with pytest.raises(ValueError) as excinfo:
        t = bazefield('non-existing-tag', start_date, end_date)
    assert 'Tag non-existing-tag not found' in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        t = bazefield('installation-04-tag-1', end_date, future_date)
    assert ('No data for {} between {} and {}'
        .format('installation-04-tag-1', end_date, future_date)
        in str(excinfo.value))

    with pytest.raises(ValueError) as excinfo:
        t = bazefield('installation-04-tag-1', start_date_no_tz, end_date)
    assert 'dates must be timezone aware' in str(excinfo.value)
