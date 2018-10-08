#!/usr/bin/env python
from camille.util import resample
import datetime as dt
import numpy as np
import pandas as pd
import pytz


d0 = dt.datetime(2018, 5, 8, tzinfo=pytz.utc)
d1 = dt.datetime(2018, 5, 9, tzinfo=pytz.utc)
d2 = dt.datetime(2018, 5, 17, tzinfo=pytz.utc)

rng_d = pd.date_range(d0, d2, freq='D')
rng_h = pd.date_range(d0, d2, freq='H')
sd = pd.Series(np.random.randn(len(rng_d)), index=rng_d)
sh = pd.Series(np.random.randn(len(rng_h)), index=rng_h)
s2 = pd.Series([-1.0, 1.0], index=[d0, d1])


def test_resample_linear():
    sr_a = resample(sd, onto=sh, interp='linear')
    sr_b = resample(sd, onto=sh.index, interp='linear')
    sr_c = resample(sh, onto=sd.index, interp='linear')

    assert sr_a.notna().all()
    assert sr_a.notnull().all()

    pd.testing.assert_series_equal(sr_a, sr_b, check_exact=True)
    pd.testing.assert_index_equal(sr_a.index, sh.index, check_exact=True)
    pd.testing.assert_index_equal(sr_a.index, sh.index, check_exact=True)
    pd.testing.assert_index_equal(sr_c.index, sd.index, check_exact=True)


def test_resample_twice():
    sr_dh = resample(sd, onto=sh, interp='linear')
    sr_dhd = resample(sr_dh, onto=sd, interp='linear')
    pd.testing.assert_series_equal(sd, sr_dhd, check_exact=True)


def test_resample_previous():
    sr_p = resample(s2, onto=sh.index, interp='prev')
    for time, value in sr_p.iteritems():
        assert value == -1.0 if time < d1 else value == 1.0


def test_resample_next():
    sr_n = resample(s2, onto=sh.index[1:], interp='next')
    assert sr_n[sr_n.index <= d1].all()
    assert sr_n[sr_n.index > d1].isna().all()
