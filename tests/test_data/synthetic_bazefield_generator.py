#!/usr/bin/env python
"""
Simple program to create synthetic bazefield data
"""

import os
import datetime
import random
import pytz
import pandas as pd
import numpy as np


def fmt_date(d):
    tz = d.strftime('%z')
    sgn = tz[0]
    hh = tz[1:3]
    mm = tz[3:]
    return d.strftime(f'%Y-%m-%dT%H.%M.%S{sgn}{hh}.{mm}')


def main():
    root = 'bazefield_data_root'
    start_date = datetime.datetime(2018, 4, 15, tzinfo=pytz.utc)
    end_date = datetime.datetime(2018, 5, 9, tzinfo=pytz.utc)
    tags = {
        'installation-04-tag-1': {
            'mean': 3.14,
            'sd': 1.17,
            'error': 0.5,
        },
        'installation-04-tag-2': {
            'mean': 1.2E32,
            'sd': 2.22,
            'error': 0.05,
        },
        'AAA....  -.-  ...0000---__aa': {
            'mean': 0.0,
            'sd': 1.0,
            'error': 0.0,
        },
        }

    assert os.path.isdir(root)

    for tag in tags.keys():
        tag_root = os.path.join(root, tag)
        if not os.path.exists(tag_root):
            os.makedirs(tag_root)

        samples = pd.date_range(start_date, end_date, freq='1H', tz=pytz.utc)
        days = pd.date_range(start_date, end_date, freq='1D', tz=pytz.utc)

        mean = tags[tag]['mean']
        sd = tags[tag]['sd']

        df = pd.DataFrame(
            data={
                't': samples,
                'q': 192,
                'v': np.random.normal(mean, sd, len(samples)),
            })

        tag_prefix = os.path.join(tag_root, tag)

        for date, next_date in zip(days[:-1], days[1:]):
            fname = f'{tag_prefix}_{fmt_date(date)}_{fmt_date(next_date)}.json.gz'
            date_df = df[(df.t >= date) & (df.t < next_date)]
            date_df.to_json(fname, compression='gzip')


if __name__ == '__main__':
    main()
