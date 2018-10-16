import os
import re
import datetime
import json
import gzip
import pytz
import pandas as pd


def _fn_start_date(fn):
    # File names are on the form:
    #     |- start_date ----------| |- end_date ------------|
    # tag_YYYY-MM-DDTHH.MM.SS+HH.MM_YYYY-MM-DDTHH.MM.SS+HH.MM.json.gz
    date_str = fn.split('_')[-2] # extract start date
    date_str = date_str.replace('.', '') # UTC offset does not support '.'
    date_fmt = "%Y-%m-%dT%H%M%S%z"
    return datetime.datetime.strptime(date_str, date_fmt)


def _fn_end_date(fn):
    date_str = fn.split('_')[-1] # extract start date
    date_str = date_str.replace('.', '') # UTC offset does not support '.'
    date_fmt = "%Y-%m-%dT%H%M%S%zjsongz"
    return datetime.datetime.strptime(date_str, date_fmt)


def _safe_read(fn, **kwargs):
    """
    TODO: Manually infer pandas read function
    """
    try:
        return pd.read_json(fn, **kwargs)
    except:
        return pd.DataFrame()


def bazefetcher(root, tzinfo=pytz.utc):
    if not os.path.isdir(root):
        raise ValueError('{} is not a directory'.format(root))

    if not isinstance(tzinfo, datetime.tzinfo):
        raise ValueError('tzinfo must be instance of datetime.tzinfo')

    def bazefetcher_internal(tag, start_date, end_date):
        if start_date.tzinfo is None or end_date.tzinfo is None:
            raise ValueError('dates must be timezone aware')

        if not start_date <= end_date:
            raise ValueError('start_date must be earlier than end_date')

        tag_root = os.path.join(root, tag)

        if not os.path.isdir(tag_root):
            raise ValueError('Tag {} not found'.format(tag))

        files = [
            os.path.join(tag_root, fn) for fn in os.listdir(tag_root)
            if _fn_start_date(fn) <= end_date
            and start_date <= _fn_end_date(fn)]

        if not files:
            raise ValueError('No data for {} between {} and {}'.format(
                tag, str(start_date), str(end_date)))

        df = pd.concat((_safe_read(fn) for fn in files), sort=True)

        df.rename(columns={
            't': 'time',
            'v': 'value',
            }, inplace=True)

        df.time = pd.to_datetime(df.time, unit='ms')
        df.set_index('time', inplace=True)
        df.index = df.index.tz_localize(tzinfo)

        try:
            ts = df.value
            ts = ts[start_date:end_date]
        except KeyError:
            pass

        if ts.empty:
            raise ValueError('No data for {} between {} and {}'.format(
                tag, str(start_date), str(end_date)))

        return ts

    return bazefetcher_internal
