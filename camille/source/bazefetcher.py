import os
from os.path import join, isdir, basename
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


def _tidy_frame(df, tzinfo):
    if df is None or df.empty:
        df.insert(0, 't', [])
        df.insert(1, 'v', [])
    df.rename(columns={
        't': 'time',
        'v': 'value',
        }, inplace=True)

    df.time = pd.to_datetime(df.time, unit='ms')
    df.set_index('time', inplace=True)
    df.index = df.index.tz_localize(tzinfo)
    df.sort_index(inplace=True)


def _get_files(src_dirs, tag, fn_regex, date_pred):
    """
    Gets all possible files with tag under src_dirs which satisfy
    fn_regex and date_func
    """
    tag_roots = list(filter(isdir, (join(dr, tag) for dr in src_dirs)))

    if not tag_roots:
        raise ValueError('Tag {} not found in {}'.format(tag, src_dirs))

    files = [join(r, fn) for r in tag_roots for fn in os.listdir(r)
             if fn_regex.match(fn) and date_pred(fn)]

    if len(src_dirs) > 1:
        fnames = list(map(basename, files))
        if len(fnames) != len(set(fnames)):
            seen = set()
            dupl = []
            for fn in fnames:
                if fn in seen:
                    dupl.append(fn)
                seen.add(fn)
            raise ValueError("files {} are not unique".format(dupl))

    return files


def _extend_bwd(start_date, df, src_dirs, tag, fn_regex, tzinfo):
    """
    Extends the range to include the last sample before or at the same time
    as the start of time range
    """

    if df.index.min() <= start_date:
        start_date = df[:start_date].index.max()
        return df, start_date

    files = _get_files(src_dirs, tag, fn_regex,
                       lambda fn: _fn_end_date(fn) < start_date)

    while True:
        if not files: break

        prev_fn = max(files, key=lambda x: _fn_end_date( os.path.basename(x) ))
        tmp_df = _safe_read(prev_fn)

        if tmp_df.empty:
            files.remove(prev_fn)
            continue

        _tidy_frame(tmp_df, tzinfo)

        start_date = tmp_df.index.max()

        df.loc[start_date] = tmp_df.loc[start_date]
        df.sort_index(inplace=True)
        break

    return df, start_date


def _extend_fwd(end_date, df, src_dirs, tag, fn_regex, tzinfo):
    """
    Extends the range to include the next sample after or at the same time
    as the end of time range
    """

    if df.index.max() >= end_date:
        end_date = df[end_date:].index.min()
        return df, end_date + datetime.timedelta(microseconds=1)

    files = _get_files(src_dirs, tag, fn_regex,
                       lambda fn: _fn_start_date(fn) > end_date)

    while True:
        if not files: break

        next_fn = min(files,
                      key=lambda x: _fn_start_date( os.path.basename(x) ))
        tmp_df = _safe_read(next_fn)

        if tmp_df.empty:
            files.remove(next_fn)
            continue

        _tidy_frame(tmp_df, tzinfo)

        end_date = tmp_df.index.min()

        df.loc[end_date] = tmp_df.loc[end_date]
        df.sort_index(inplace=True)
        end_date += datetime.timedelta(microseconds=1)
        break

    return df, end_date


def bazefetcher(src_dir, tzinfo=pytz.utc):
    """Bazefetcher

    Creates a function that can be used to read time series' from specified
    root directories

    Parameters
    ----------
    src_dir : str or iterable of str
        Path to the bazefetcher root directories
    tzinfo :datetime.tzinfo
        Time series timezone

    Returns
    -------
    function (str, datetime.datetime, datetime.datetime, str)
        Function for reading time series from the root directories. Tag split
        across directories is supported as long as all filenames are unique.

        tag : str
            The tag of the series to read
        start : datetime.datetime
            The start time of the data to be read. Must be timezone aware
        end : datetime.datetime
            The end time of the data to be read. Must be timezone aware
        snap : str
            'left', 'right' or 'both' (default None).
            Direction in which returned data should be extended

        Returns
        -------
        pandas.TimeSeries
           Result time series

    Examples
    --------

    Read time series `series` with tag `tag`:

    >>> start_date = datetime.datetime(2029, 1, 1, tzinfo=pytz.utc)
    >>> end_date = datetime.datetime(2030, 1, 1, tzinfo=pytz.utc)
    >>> cin = camille.source.bazefetcher('<root-directory>')
    >>> ts = cin('tag', start_date, end_date)

    >>> cin = camille.source.bazefetcher(
    ...           ['tests/test_data/baze', 'tests/test_data/authored'])
    >>> ts = cin('Perlin', start_date, end_date, snap='both')
    """
    if isinstance(src_dir, str):
        src_dir = [src_dir]

    src_dirs = [dr for dr in src_dir if isdir(dr)]
    if not src_dirs:
        raise ValueError('no file in {} is a directory'.format(src_dir))

    if not isinstance(tzinfo, datetime.tzinfo):
        raise ValueError('tzinfo must be instance of datetime.tzinfo')

    def bazefetcher_internal(tag,
                             start_date=datetime.datetime(1677, 9, 22, tzinfo=pytz.utc),
                             end_date=datetime.datetime(2262, 4, 11, tzinfo=pytz.utc),
                             snap=None):
        if start_date.tzinfo is None or end_date.tzinfo is None:
            raise ValueError('dates must be timezone aware')

        if not start_date <= end_date:
            raise ValueError('start_date must be earlier than end_date')

        fn_regex = re.compile(tag + fn_tail_pattern)

        files = _get_files(src_dirs, tag, fn_regex,
                           lambda fn : _fn_start_date(fn) <= end_date
                                       and start_date <= _fn_end_date(fn))

        L = [_safe_read(fn) for fn in files]
        df = pd.concat(L, sort=True) if len(L) > 0 else pd.DataFrame()

        _tidy_frame(df, tzinfo)

        if snap == 'left' or snap == 'both':
            df, start_date = _extend_bwd(start_date,
                                         df,
                                         src_dirs,
                                         tag,
                                         fn_regex,
                                         tzinfo)

        if snap == 'right' or snap == 'both':
            df, end_date = _extend_fwd(end_date,
                                       df,
                                       src_dirs,
                                       tag,
                                       fn_regex,
                                       tzinfo)

        try:
            eps = datetime.timedelta(microseconds=1)
            ts = df.value
            ts = ts[start_date:end_date - eps]
        except KeyError:
            pass

        return ts

    return bazefetcher_internal
