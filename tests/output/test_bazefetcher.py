from datetime import datetime, timedelta
from pytz import utc, timezone
from camille.output import Bazefetcher as Bazeoutput
from camille.source import Bazefetcher as Bazesource
import numpy as np
import os
import pandas as pd
import pytest

eps = timedelta(microseconds=1)

def assert_correctly_loaded(expected, basedir, t0, t1, tag="test",
                            tzinfo=utc):
    bazein = Bazesource(str(basedir))
    result = bazein(tag, t0, t1)

    new_index = result.index.tz_convert(tzinfo)
    result = result.reindex(new_index)
    pd.testing.assert_series_equal(expected, result)


def assert_correct_index(expected_index, basedir, start_date, end_date,
                         tag="test"):
    bazein = Bazesource(str(basedir))
    result = bazein(tag, start_date, end_date)

    assert result.size == len(expected_index)
    assert (result.index == expected_index).all()


def assert_correct_raw_values(expected_series, basedir, file_date, tag="test"):
    fname = get_test_fname(file_date, tag)
    path = os.path.join(str(basedir), tag, fname)
    df = pd.read_json(path)
    assert np.allclose(df.v.values, expected_series.values)


def get_files_count(basedir, tag="test"):
    path = os.path.join(str(basedir), tag)
    if (os.path.isdir(path)):
        return len(os.listdir(path))
    else:
        return 0


def assert_files_list(basedir, start_date, days, tag="test"):
    """
    Asserts file list output is as expected and contains only all
    expected files from start_date
    """
    flist = os.listdir(os.path.join(str(basedir), tag))
    flist.sort()

    expected_list = [get_test_fname(date, tag)
                     for date in
                     pd.date_range(start_date, periods=days).tolist()]
    assert flist == expected_list


def get_test_fname(start_date, tag):
    """
    Gets expected filename of output file. End_day would be the next day
    """
    end_date = start_date + timedelta(days=1)
    format_string = "{:0>2d}"
    start_day = format_string.format(start_date.day)
    end_day = format_string.format(end_date.day)
    start_month = format_string.format(start_date.month)
    end_month = format_string.format(end_date.month)

    return ("{}_{}-{}-{}T00.00.00+00.00_{}-{}-{}T00.00.00+00.00.json.gz"
            .format(tag, start_date.year, start_month, start_day,
                    end_date.year, end_month, end_day))


def test_one_day_one_file(tmpdir):
    t0 = datetime(2018, 1, 1, 10, tzinfo=utc)
    t1 = datetime(2018, 1, 1, 13, tzinfo=utc)

    rng = pd.date_range(t0, t1, freq='H', name="time", closed='left')
    data = np.random.randn(len(rng))
    ts = pd.Series(data, name="value", index=rng)

    bazeout = Bazeoutput(str(tmpdir))
    bazeout(ts, "test", t0, t1)

    assert_files_list(tmpdir, t0, 1)
    assert_correctly_loaded(ts, tmpdir, t0, t1)


def test_two_days_two_files(tmpdir):
    t0 = datetime(2018, 1, 31, 23, tzinfo=utc)
    t1 = datetime(2018, 2, 1, 3, 1, tzinfo=utc)

    rng = pd.date_range(t0, t1, freq='30T', name="time")
    data = np.array(range(9), dtype=np.int64)
    ts = pd.Series(data, name="value", index=rng)
    generate_output(tmpdir, ts, t0, t1)

    assert_files_list(tmpdir, t0, 2)
    assert_correctly_loaded(ts, tmpdir, t0, t1)


def test_output_interval(tmpdir):
    t_rng_start = get_test_date(1, 12)
    t_rng_end = get_test_date(2, 4)

    rng = get_test_index(t_rng_start, t_rng_end)
    ts = get_test_series(rng=rng)

    t_data_start = get_test_date(1, 13, 30)
    t_data_end = get_test_date(1, 15, 30)

    generate_output(tmpdir, ts, t_data_start, t_data_end)

    expected_times = [get_test_date(1, 14),
                      get_test_date(1, 15)]
    assert_correct_index(expected_times, tmpdir, t_rng_start, t_rng_end)


def test_24_hours_midnight_file(tmpdir):
    """
    For 24 hours time range from midnight to midnight (right border
    opened) only 1 file is expected
    """

    t0 = get_test_date(6)
    t1 = get_test_date(7)

    ts = get_test_series(t0, t1)
    generate_output(tmpdir, ts, t0, t1)

    assert_files_list(tmpdir, t0, 1)
    assert_correctly_loaded(ts, tmpdir, t0, t1)


def test_no_utc(tmpdir):
    tzinfo = timezone("Australia/Melbourne")
    tz_day = 15
    start_hour = 8
    end_hour = 12
    t0 = get_test_date(tz_day, start_hour, tzinfo=tzinfo)
    t1 = get_test_date(tz_day, end_hour, tzinfo=tzinfo)

    data = np.array([x for x in range(start_hour, end_hour)], dtype=np.int64)
    ts = get_test_series(t0, t1, data=data)
    generate_output(tmpdir, ts, t0, t1)

    assert_files_list(tmpdir, t0.astimezone(utc), 2)
    assert_correctly_loaded(ts, tmpdir, t0, t1, tzinfo=tzinfo)


def test_no_dates_provided(tmpdir):
    """
    Tests output takes full series range if no boundaries provided
    For reference purpose uses dates with daylight saving in range
    """
    tzinfo = timezone("CET")
    tz_day = 28
    tz_month = 10
    start_hour = 1
    end_hour = 4
    t0 = get_test_date(tz_day, start_hour, month=tz_month, tzinfo=tzinfo)
    t1 = get_test_date(tz_day, end_hour, month=tz_month, tzinfo=tzinfo)

    rng = get_test_index(t0, t1)
    data = list(map(lambda d: d.isoformat(), rng.to_pydatetime()))
    ts = get_test_series(t0, t1, data=data, rng=rng)
    generate_output(tmpdir, ts)

    assert_files_list(tmpdir, t0.astimezone(utc), 2)
    expected_times = pd.date_range(t0, t1, freq="H", closed="left")
    assert_correct_index(expected_times, tmpdir, t0, t1)


def test_writing_empty_data(tmpdir):
    t0 = get_test_date(6)
    t1 = get_test_date(7)
    ts = pd.Series(dtype='float64')

    files_before = get_files_count(tmpdir)
    generate_output(tmpdir, ts, t0, t1)
    files_after = get_files_count(tmpdir)
    assert files_before == files_after


def test_writing_empty_data_no_daterange(tmpdir):
    ts = pd.Series(dtype='float64')
    files_before = get_files_count(tmpdir)
    generate_output(tmpdir, ts)
    files_after = get_files_count(tmpdir)
    assert files_before == files_after


def test_multiple_writes_to_same_file(tmpdir):
    t0 = datetime(2018, 1, 1, 5, tzinfo=utc)
    t1 = datetime(2018, 1, 1, 10, tzinfo=utc)
    t2 = datetime(2018, 1, 1, 15, tzinfo=utc)

    rng = pd.date_range(t0, t2, freq='H', name="time", closed='left')
    data = np.random.randn(len(rng))
    ts = pd.Series(data, name="value", index=rng)

    bazeout = Bazeoutput(str(tmpdir))
    bazeout(ts, "test", t0, t1)
    bazeout(ts, "test", t1, t2)

    assert_files_list(tmpdir, t0, 1)
    assert_correctly_loaded(ts, tmpdir, t0, t2)


def test_multiple_writes_to_same_file_fill(tmpdir):
    t0 = datetime(2018, 1, 1, 5, tzinfo=utc)
    t1 = datetime(2018, 1, 1, 10, tzinfo=utc)
    t2 = datetime(2018, 1, 1, 15, tzinfo=utc)
    t3 = datetime(2018, 1, 1, 20, tzinfo=utc)

    rng = pd.date_range(t0, t3, freq='H', name="time", closed='left')
    data = np.random.randn(len(rng))
    ts = pd.Series(data, name="value", index=rng)
    data2 = data + 1
    ts2 = pd.Series(data2, name="value", index=rng)

    bazeout = Bazeoutput(str(tmpdir))
    bazeout(ts, "test", t0, t1)
    bazeout(ts, "test", t2, t3)
    bazeout(ts2, "test", t0, t3, fill=True)

    expected = pd.concat([
        ts[:t1 - eps],
        ts2[t1:t2 - eps],
        ts[t2:]
    ], sort=True)

    assert_files_list(tmpdir, t0, 1)
    assert_correctly_loaded(expected, tmpdir, t0, t3)
    assert_correct_raw_values(expected, tmpdir, t0)



def test_multiple_writes_to_same_file_with_overlap_no_overwrite(tmpdir):
    t0 = datetime(2018, 1, 1, 5, tzinfo=utc)
    t1 = datetime(2018, 1, 1, 8, tzinfo=utc)
    t2 = datetime(2018, 1, 1, 10, tzinfo=utc)
    t3 = datetime(2018, 1, 1, 15, tzinfo=utc)

    rng = pd.date_range(t0, t3, freq='H', name="time", closed='left')
    data = np.random.randn(len(rng))
    ts = pd.Series(data, name="value", index=rng)

    bazeout = Bazeoutput(str(tmpdir))
    bazeout(ts, "test", t1, t2)

    with pytest.raises(ValueError):
        bazeout(ts, "test", t0, (t2 - eps))
    with pytest.raises(ValueError):
        bazeout(ts, "test", (t1 + eps), t3)
    with pytest.raises(ValueError):
        bazeout(ts, "test", (t1 + eps), (t2 - eps))
    with pytest.raises(ValueError):
        bazeout(ts, "test", t0, t3)

    assert_files_list(tmpdir, t0, 1)
    assert_correctly_loaded(ts[t1:(t2-eps)], tmpdir, t1, t2)


def test_multiple_writes_to_same_file_with_right_overlap_overwrite(tmpdir):
    t0 = datetime(2018, 1, 1, 5, tzinfo=utc)
    t1 = datetime(2018, 1, 1, 8, tzinfo=utc)
    t2 = datetime(2018, 1, 1, 10, tzinfo=utc)
    t3 = datetime(2018, 1, 1, 15, tzinfo=utc)

    rng = pd.date_range(t0, t3, freq='H', name="time", closed='left')
    data = np.random.randn(len(rng))
    ts = pd.Series(data, name="value", index=rng)
    data2 = data + 1
    ts2 = pd.Series(data2, name="value", index=rng)

    bazeout = Bazeoutput(str(tmpdir))
    bazeout(ts, "test", t0, t2)
    bazeout(ts2, "test", t1, t3, overwrite=True)

    expected = pd.concat([ts[:(t1-eps)], ts2[t1:]],
                         sort=True)
    assert_files_list(tmpdir, t0, 1)
    assert_correctly_loaded(expected, tmpdir, t0, t3)
    assert_correct_raw_values(expected, tmpdir, t0)


def test_multiple_writes_to_same_file_with_left_overlap_overwrite(tmpdir):
    t0 = datetime(2018, 1, 1, 5, tzinfo=utc)
    t1 = datetime(2018, 1, 1, 8, tzinfo=utc)
    t2 = datetime(2018, 1, 1, 10, tzinfo=utc)
    t3 = datetime(2018, 1, 1, 15, tzinfo=utc)

    rng = pd.date_range(t0, t3, freq='H', name="time", closed='left')
    data = np.random.randn(len(rng))
    ts = pd.Series(data, name="value", index=rng)
    data2 = data + 1
    ts2 = pd.Series(data2, name="value", index=rng)

    bazeout = Bazeoutput(str(tmpdir))
    bazeout(ts, "test", t1, t3)
    bazeout(ts2, "test", t0, t2, overwrite=True)

    expected = pd.concat([ts2[:(t2-eps)], ts[t2:]],
                         sort=True)
    assert_files_list(tmpdir, t0, 1)
    assert_correctly_loaded(expected, tmpdir, t0, t3)
    assert_correct_raw_values(expected, tmpdir, t0)


def test_multiple_writes_to_same_file_with_internal_overlap_overwrite(tmpdir):
    t0 = datetime(2018, 1, 1, 5, tzinfo=utc)
    t1 = datetime(2018, 1, 1, 8, tzinfo=utc)
    t2 = datetime(2018, 1, 1, 10, tzinfo=utc)
    t3 = datetime(2018, 1, 1, 15, tzinfo=utc)

    rng = pd.date_range(t0, t3, freq='H', name="time", closed='left')
    data = np.random.randn(len(rng))
    ts = pd.Series(data, name="value", index=rng)
    data2 = data + 1
    ts2 = pd.Series(data2, name="value", index=rng)

    bazeout = Bazeoutput(str(tmpdir))
    bazeout(ts, "test", t0, t3)
    bazeout(ts2, "test", t1, t2, overwrite=True)

    expected = pd.concat([ts[:t1-eps], ts2[t1:(t2-eps)], ts[t2:]],
                         sort=True)
    assert_files_list(tmpdir, t0, 1)
    assert_correctly_loaded(expected, tmpdir, t0, t3)
    assert_correct_raw_values(expected, tmpdir, t0)


def test_multiple_writes_to_same_file_with_full_overlap_overwrite(tmpdir):
    t0 = datetime(2018, 1, 1, 5, tzinfo=utc)
    t1 = datetime(2018, 1, 1, 15, tzinfo=utc)

    rng = pd.date_range(t0, t1, freq='H', name="time", closed='left')
    data = np.random.randn(len(rng))
    ts = pd.Series(data, name="value", index=rng)
    data2 = data + 1
    ts2 = pd.Series(data2, name="value", index=rng)

    bazeout = Bazeoutput(str(tmpdir))
    bazeout(ts, "test", t0, t1)
    bazeout(ts2, "test", t0, t1, overwrite=True)

    assert_files_list(tmpdir, t0, 1)
    assert_correctly_loaded(ts2, tmpdir, t0, t1)
    assert_correct_raw_values(ts2, tmpdir, t0)


def get_test_date(day, hour=0, minute=0, second=0, year=2018,
                  month=1, tzinfo=utc):
    naive_datetime = datetime(year, month, day, hour, minute, second)
    return tzinfo.localize(naive_datetime)


def get_test_index(start, end):
    return pd.date_range(start, end, freq='H', name="time", closed='left')


def get_test_series(start_date=None, end_date=None,
                    data=None, rng=None):
    """
    Generates test pd.series sequence. Unless provided
    otherwise, uses random data in start_date/end_date range.
    For default time sequence sets hourly interval, closed
    from the left side.
    """
    rng = get_test_index(start_date, end_date) if rng is None else rng
    data = np.random.randn(len(rng)) if data is None else data
    return pd.Series(data, name="value", index=rng)


def generate_output(basedir, ts, start_date=None, end_date=None, tag="test"):
    bazeout = Bazeoutput(str(basedir))
    bazeout(ts, tag, start_date, end_date)
