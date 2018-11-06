from datetime import datetime
from pytz import utc
import camille.output
import camille.source
import numpy as np
import os
import pandas as pd


def assert_correctly_loaded(expected, tag, basedir, t0, t1):
    bazein = camille.source.bazefetcher(basedir)
    result = bazein(tag, t0, t1)
    pd.testing.assert_series_equal(expected, result)


def test_one_day_one_file(tmpdir):
    t0 = datetime(2018, 1, 1, 10, tzinfo=utc)
    t1 = datetime(2018, 1, 1, 13, tzinfo=utc)
    rng = pd.date_range(t0, t1, freq='H', name='time', closed='left')
    ts = pd.Series(np.random.randn(len(rng)), name='value', index=rng)

    bazeout = camille.output.bazefetcher(str(tmpdir))
    bazeout(ts, 'test', t0, t1)

    assert (os.listdir(os.path.join( str(tmpdir), 'test' ))
        == ['test_2018-01-01T00.00.00+00.00_2018-01-02T00.00.00+00.00.json.gz'])
    assert_correctly_loaded(ts, 'test', str(tmpdir), t0, t1)


def test_two_days_two_files(tmpdir):
    t0 = datetime(2018, 1, 1, 23, tzinfo=utc)
    t1 = datetime(2018, 1, 2, 3, tzinfo=utc)
    rng = pd.date_range(t0, t1, freq='H', name='time', closed='left')
    ts = pd.Series(np.array([1,2,3,4]), name='value',index=rng)

    bazeout = camille.output.bazefetcher(str(tmpdir))
    bazeout(ts, 'test', t0, t1)

    flist = os.listdir(os.path.join(str(tmpdir), 'test'))
    flist.sort()
    assert len(flist) == 2
    assert (flist[0]
        == 'test_2018-01-01T00.00.00+00.00_2018-01-02T00.00.00+00.00.json.gz')
    assert (flist[1]
        == 'test_2018-01-02T00.00.00+00.00_2018-01-03T00.00.00+00.00.json.gz')

    assert_correctly_loaded(ts, 'test', str(tmpdir), t0, t1)


def test_output_interval(tmpdir):
    t00 = datetime(2018, 1, 1, 12, tzinfo=utc)
    t10 = datetime(2018, 1, 2, 4, tzinfo=utc)
    rng = pd.date_range(t00, t10, freq='H', name='time', closed='left')
    ts = pd.Series(np.random.randn(len(rng)), index=rng)

    t01 = datetime(2018, 1, 1, 13, 30, tzinfo=utc)
    t11 = datetime(2018, 1, 1, 15, 30, tzinfo=utc)

    bazeout = camille.output.bazefetcher(str(tmpdir))
    bazeout(ts, 'test', t01, t11)

    bazein = camille.source.bazefetcher(str(tmpdir))
    result = bazein('test', t00, t10)

    assert result.size == 2

    expected_times = [datetime(2018, 1, 1, 14, tzinfo=utc),
                      datetime(2018, 1, 1, 15, tzinfo=utc)]
    assert (result.index == expected_times).all()
