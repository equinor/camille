#!/usr/bin/env python
"""
Simple program to create synthetic windiris data
"""

from datetime import datetime
from itertools import cycle
from pytz import utc
from noise import pnoise2
import os
import pandas as pd


def perlin(x, y, yoffset, xscale=0.01, yscale=0.133):
    return pnoise2(x * xscale, y * yscale + yoffset)


def main():
    root = 'windiris'
    start_date = datetime(2030, 1, 1, tzinfo=utc)
    end_date = datetime(2030, 1, 4, tzinfo=utc)

    times = pd.date_range(start_date, end_date, freq='S', tz=utc).repeat(10)
    distances = cycle(
        [50.0, 80.0, 120.0, 160.0, 200.0, 240.0, 280.0, 320.0, 360.0, 400.0])
    los_ids = cycle(pd.Series([0, 1, 2, 3]).repeat(10))
    rowc = len(times)

    tilt = pd.Series([perlin(x, 10, 0) for x in range(rowc // 10)]).repeat(10)
    roll = pd.Series([perlin(x, 11, 0) for x in range(rowc // 10)]).repeat(10)
    tilt = tilt + 1
    roll = roll + 1

    rws = pd.Series([perlin(x, y, 0) for x in range(rowc // 10) for y in range(10)])
    rws = (rws + 1) * 5


    df = pd.DataFrame({
        'LOS index': [next(los_ids) for _ in range(rowc)],
        'Distance': [next(distances) for _ in range(rowc)],
        'RWS': rws.values,
        'DRWS': 0,
        'CNR': 0,
        'Tilt': tilt.values,
        'Roll': roll.values,
        'RWS Status': 1,
        'Overrun Status': 1,
    }, index=times)

    for d in df.groupby(df.index.date):
        date = d[0]
        dfd = d[1].copy()
        dfd.insert(0, 'Timestamp',
            dfd.index.map(lambda a: a.strftime('%Y-%m-%d %H:%M:%S.%f')))

        fname = os.path.join(root, date.strftime('WI_%Y-%m-%d.csv'))
        os.makedirs(root, exist_ok=True)
        dfd.to_csv(fname, index=False, sep=';')


if __name__ == '__main__':
    main()
