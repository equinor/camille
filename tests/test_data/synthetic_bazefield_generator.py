#!/usr/bin/env python
"""
Simple program to create synthetic bazefield data
"""

from camille.output import bazefetcher as bzdst
from datetime import datetime
from math import pi
from noise import pnoise2
from pytz import utc
import numpy as np
import pandas as pd



@np.vectorize
def perlin(x, y, xscale=0.002, yscale=0.125, xoffset=0.0, yoffset=0.0):
    return pnoise2(x * xscale + xoffset, y * yscale + yoffset)


def main():
    bout = bzdst('baze')
    aout = bzdst('authored')

    t0 = datetime(2030, 1, 1, tzinfo=utc)
    tn = datetime(2030, 1, 5, tzinfo=utc)
    trng = pd.date_range(t0, tn, freq="S", closed='left')
    t = trng.map(lambda t: (t - t0).total_seconds())

    sin_t60s_sr1hz = pd.Series(np.sin(t * pi / 60), index=trng)
    cos_t60s_sr1hz = pd.Series(np.cos(t * pi / 60), index=trng)
    tan_t60s_sr1hz = pd.Series(np.tan(t * pi / 60), index=trng)
    bout(sin_t60s_sr1hz, 'Sin-T60s-SR1hz')
    bout(cos_t60s_sr1hz, 'Cos-T60s-SR1hz')
    bout(tan_t60s_sr1hz, 'Tan-T60s-SR1hz')

    signal = pd.Series(perlin(t, 0), index=trng)
    bout(signal, 'Perlin')

    i04_status = pd.Series(
        [1, 0, 1, 0, 1],
        index=[
            t0,
            datetime(2030, 1, 2, tzinfo=utc),
            datetime(2030, 1, 2, 22, tzinfo=utc),
            datetime(2030, 1, 2, 23, 30, 30, tzinfo=utc),
            datetime(2030, 1, 3, tzinfo=utc),
        ]
    )
    aout(i04_status, 'installation-04-status', end=tn)



if __name__ == '__main__':
    main()
