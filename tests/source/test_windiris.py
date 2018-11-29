#!/usr/bin/env python3
from camille.source import windiris
from datetime import datetime

wi = windiris('tests/test_data/windiris')

def test_load_all_data():
    s = datetime(2017, 12, 17)
    e = datetime(2018, 10, 23)

    df = wi('inst2', s, e)

    assert df.shape[0] == 27
    assert (
                df.RWS == [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                            2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
                            3, 3, 3, 3, 3, 3 ]
           ).all()


def test_load_one_day():
    s = datetime(2017, 12, 17)
    e = datetime(2017, 12, 18)

    df = wi('inst2', s, e)

    assert df.shape[0] == 11
    assert (
                df.RWS == [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ]
           ).all()

    s = datetime(2017, 12, 18)
    e = datetime(2017, 12, 19)

    df = wi('inst2', s, e)

    assert df.shape[0] == 10
    assert (
                df.RWS == [ 2, 2, 2, 2, 2, 2, 2, 2, 2, 2 ]
           ).all()

def test_left_closed():
    s = datetime(2018, 10, 22, 8, 30, 0, 603438)
    e = datetime(2018, 10, 23)

    df = wi('inst2', s, e)

    assert df.shape[0] == 6
    assert (
                df.RWS == [ 3, 3, 3, 3, 3, 3 ]
           ).all()

def test_right_open():
    s = datetime(2017, 12, 17)
    e = datetime(2017, 12, 18, 16,30, 0, 603437)

    df = wi('inst2', s, e)

    assert df.shape[0] == 11
    assert (
                df.RWS == [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ]
           ).all()
