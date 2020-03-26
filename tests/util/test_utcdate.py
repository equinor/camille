#!/usr/bin/env python
from camille.util import utcdate
from datetime import datetime
import pytz


def test_utcdate_new_date():
    date = utcdate(year=2030, month=1, day=1)
    assert date.tzinfo == pytz.utc
    assert date.isoformat() == '2030-01-01T00:00:00+00:00'


def test_utcdate_local_date():
    date = datetime(2030, 1, 1)
    as_utc = utcdate(date)

    assert as_utc.tzinfo == pytz.utc
    assert as_utc.isoformat() == '2030-01-01T00:00:00+00:00'


def test_utcdate_other_timezone():
    oslo = pytz.timezone('Europe/Oslo').localize(datetime(2030, 1, 1, 10, 0, 0))
    as_utc = utcdate(oslo)

    assert as_utc.tzinfo == pytz.utc
    assert as_utc.isoformat() == '2030-01-01T09:00:00+00:00'
