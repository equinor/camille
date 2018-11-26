import os
import re
import datetime
import pytz
import pandas as pd


date_pattern = r'[0-9]{4}-[0-9]{2}-[0-9]{2}'
time_pattern = r'[0-9]{2}\.[0-9]{2}\.[0-9]{2}\+[0-9]{2}\.[0-9]{2}'
dt_pattern = date_pattern + 'T' + time_pattern
fn_tail_pattern = '_' + dt_pattern + '_' + dt_pattern + r'\.json\.gz$'


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

        fn_regex = re.compile(tag + fn_tail_pattern)

        files = [
            os.path.join(tag_root, fn) for fn in os.listdir(tag_root)
            if fn_regex.match(fn)
                and _fn_start_date(fn) <= end_date
                and start_date <= _fn_end_date(fn)
        ]
        files.sort()

        L = [_safe_read(fn) for fn in files]
        df = pd.concat(L, sort=True) if len(L) > 0 else None

        if not files or df is None or df.empty:
            df = pd.DataFrame(columns=('t', 'v'))

        df.rename(columns={
            't': 'time',
            'v': 'value',
            }, inplace=True)

        df.time = pd.to_datetime(df.time, unit='ms')
        df.set_index('time', inplace=True)
        df.index = df.index.tz_localize(tzinfo)
        df.sort_index(inplace=True)

        try:
            eps = datetime.timedelta(microseconds=1)
            ts = df.value
            ts = ts[start_date:end_date - eps]
        except KeyError:
            pass

        return ts

    return bazefetcher_internal
