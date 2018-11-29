#!/usr/bin/env python3
from camille.source import windiris
from datetime import datetime

def test_load_all_data():
    s = datetime(2017, 12, 17)
    e = datetime(2018, 10, 23)

    wi = windiris('tests/test_data/windiris')
    df = wi(s, e, 'inst2')

    assert df.shape[0] == 27
    assert (
                df.RWS == [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                            2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
                            3, 3, 3, 3, 3, 3 ]
           ).all()


def test_load_one_day():
    s = datetime(2017, 12, 17)
    e = datetime(2017, 12, 18)

    wi = windiris('tests/test_data/windiris')
    df = wi(s, e, 'inst2')

    assert df.shape[0] == 11
    assert (
                df.RWS == [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ]
           ).all()

    s = datetime(2017, 12, 18)
    e = datetime(2017, 12, 19)

    wi = windiris('tests/test_data/windiris')
    df = wi(s, e, 'inst2')

    assert df.shape[0] == 10
    assert (
                df.RWS == [ 2, 2, 2, 2, 2, 2, 2, 2, 2, 2 ]
           ).all()
