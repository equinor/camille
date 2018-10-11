import os
import pandas as pd
import numpy as np
import datetime
import pytz
import camille.source
import camille.output


def is_correctly_loaded_from_basefetcher( expected, tag, basedir ):
    bazein = camille.source.bazefetcher( basedir )
    result = bazein( tag, expected.index[0], expected.index[-1] )

    return (expected.index == result.index).all() \
       and np.allclose( expected.values, result.values )


def test_one_day_one_file(tmpdir):
    rng = pd.date_range( start='1/1/2018T10:00',
                         end='1/1/2018T12:00',
                         freq='H', tz='utc' )
    ts = pd.Series(np.random.randn(len(rng)), index=rng)

    bazeout = camille.output.bazefetcher( tmpdir.dirname )
    bazeout( ts, 'test', ts.index[0], ts.index[-1] )

    assert len( os.listdir( tmpdir.dirname + '/test' ) ) == 1
    assert is_correctly_loaded_from_basefetcher( ts, 'test', tmpdir.dirname )


def test_two_days_two_files(tmpdir):
    rng = pd.date_range( start='1/1/2018T23:00',
                         end='1/2/2018T02:00',
                         freq='H', tz='utc' )
    ts = pd.Series(np.random.randn(len(rng)), index=rng)

    bazeout = camille.output.bazefetcher( tmpdir.dirname )
    bazeout( ts, 'test', ts.index[0], ts.index[-1] )

    assert len( os.listdir( os.path.join( tmpdir.dirname, 'test' ) ) ) == 2
    assert is_correctly_loaded_from_basefetcher( ts, 'test', tmpdir.dirname )


def test_output_interval(tmpdir):
    rng = pd.date_range( start='1/1/2018T12:00',
                         end='1/1/2018T16:00',
                         freq='H', tz='utc' )
    ts = pd.Series(np.random.randn(len(rng)), index=rng)

    start = datetime.datetime( 2018, 1, 1, 13, 30, tzinfo=pytz.utc )
    end = datetime.datetime( 2018, 1, 1, 15, 30, tzinfo=pytz.utc )

    bazeout = camille.output.bazefetcher( tmpdir.dirname )
    bazeout( ts, 'test', start, end )

    bazein = camille.source.bazefetcher( tmpdir.dirname )
    result = bazein( 'test', ts.index[0], ts.index[-1] )

    assert result.size == 2

    expected_times = [ datetime.datetime( 2018, 1, 1, 14, tzinfo=pytz.utc),
                       datetime.datetime( 2018, 1, 1, 15, tzinfo=pytz.utc) ]
    assert (result.index == expected_times).all()
