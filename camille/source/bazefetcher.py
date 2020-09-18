import os
from os.path import join, isdir, basename
import re
import datetime
import pytz
import pandas as pd
from collections import abc
from math import ceil

class TagNotFoundError(ValueError):
    pass

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


def _tidy_frame(df, tzinfo):
    if df is None or df.empty or 't' not in df.columns:
        df.drop(df.index, inplace=True)
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
        raise TagNotFoundError('Tag {} not found in {}'.format(tag, src_dirs))

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


def _get_fn_regex(tag):
    return re.compile(re.escape(tag) + fn_tail_pattern)


def _get_files_between_start_and_end(src_dirs, tag, start_dt, end_dt):
    return _get_files(
        src_dirs,
        tag,
        _get_fn_regex(tag),
        lambda fn: _fn_start_date(fn) < end_dt and _fn_end_date(fn) > start_dt
    )


def _extend_bwd(start_date, df, src_dirs, tag, fn_regex, tzinfo):
    """
    Extends the range to include the last sample before or at the same time
    as the start of time range
    """

    if df.index.min() <= start_date:
        start_date = df[:start_date].index.max()
        return df, start_date

    files = _get_files(src_dirs, tag, fn_regex,
                       lambda fn: _fn_end_date(fn) <= start_date)

    while True:
        if not files: break

        prev_fn = max(files, key=lambda x: _fn_end_date( os.path.basename(x) ))
        tmp_df = pd.read_json(prev_fn)

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
                       lambda fn: _fn_start_date(fn) >= end_date)

    while True:
        if not files: break

        next_fn = min(files,
                      key=lambda x: _fn_start_date( os.path.basename(x) ))
        tmp_df = pd.read_json(next_fn)

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


class Bazefetcher:
    """Bazefetcher

    Callable object that can be used to read time series from specified root
    directories. Tag split across directories is supported as long as all
    filenames are unique.

    Attributes
    ----------
    src_dir : str or iterable of str
        Path to the bazefetcher root directories
    tzinfo :datetime.tzinfo
        Time series timezone

    Examples
    --------

    Read time series `series` with tag `tag`:

    >>> start_date = datetime.datetime(2029, 1, 1, tzinfo=pytz.utc)
    >>> end_date = datetime.datetime(2030, 1, 1, tzinfo=pytz.utc)
    >>> cin = camille.source.Bazefetcher('<root-directory>')
    >>> ts = cin('tag', start_date, end_date)

    >>> cin = camille.source.Bazefetcher(
    ...           ['tests/test_data/baze', 'tests/test_data/authored'])
    >>> ts = cin('Perlin', start_date, end_date, snap='both')
    """

    def __init__(self, src_dir, tzinfo=pytz.utc):
        if isinstance(src_dir, str):
            src_dir = [src_dir]

        src_dirs = [dr for dr in src_dir if isdir(dr)]
        if not src_dirs:
            raise ValueError('no file in {} is a directory'.format(src_dir))

        if not isinstance(tzinfo, datetime.tzinfo):
            raise ValueError('tzinfo must be instance of datetime.tzinfo')

        self.src_dirs = src_dirs
        self.tzinfo = tzinfo

    def __call__(self,
                 tag,
                 start_date=datetime.datetime(1677, 9, 22, tzinfo=pytz.utc),
                 end_date=datetime.datetime(2262, 4, 11, tzinfo=pytz.utc),
                 snap=None):
        """
        Parameters
        ----------
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
            Loaded time series
        """
        if start_date.tzinfo is None or end_date.tzinfo is None:
            raise ValueError('dates must be timezone aware')

        if not start_date <= end_date:
            raise ValueError('start_date must be earlier than end_date')

        files = _get_files_between_start_and_end(
            self.src_dirs, tag, start_date, end_date)

        L = [pd.read_json(fn) for fn in files]
        df = pd.concat(L, sort=True) if len(L) > 0 else pd.DataFrame()

        _tidy_frame(df, self.tzinfo)
        fn_regex = _get_fn_regex(tag)

        if snap == 'left' or snap == 'both':
            df, start_date = _extend_bwd(start_date,
                                         df,
                                         self.src_dirs,
                                         tag,
                                         fn_regex,
                                         self.tzinfo)

        if snap == 'right' or snap == 'both':
            df, end_date = _extend_fwd(end_date,
                                       df,
                                       self.src_dirs,
                                       tag,
                                       fn_regex,
                                       self.tzinfo)

        try:
            eps = datetime.timedelta(microseconds=1)
            ts = df.value
            ts = ts[start_date:end_date - eps]
        except KeyError:
            pass

        return ts


    def create_iterator(self, tags, start=None, end=None,
                        interval=datetime.timedelta(1),
                        padding=datetime.timedelta(0), leftpad=True,
                        rightpad=False, tag_kwargs=None):
        return BazeIter(self, tags, start=start, end=end, interval=interval,
                        padding=padding, leftpad=leftpad, rightpad=rightpad,
                        tag_kwargs=tag_kwargs)

class BazeIter(abc.Iterable, abc.Sized):
    """Bazefetcher iterator


    Creates pandas.Series from camille.source.bazefetcher() as iterations of the
    time range [start, stop> at given intervals. Returns the Pandas.Series,
    start, stop for each iteration. The timerange for the returned Pandas.Series
    includes (optional) padding, while the start and stop does not.


    Returns
    -------

    data : pandas.Series or dict of pandas.Series
        The series gathered from the baze-function for each iteration. If a list
        of tags is provided a dict is returned mapping tags to corresponding
        series.
        Includes padding
    start : list of datetime.datetime
        The start dates for all iterations. Does not include padding
    end : list of datetime.datetime
        The end time for all iterations. Does not include padding



    See Also
    --------

    camille.source.bazefetcher

    Notes
    -----

     .. versionadded:: 1.0

    Examples
    --------

    Read 'series' from 'tag':

    >>> baze = camille.source.bazefetcher(root)
    >>> start_date = datetime.datetime(..., tzinfo=utc)
    >>> end_date = datetime.datetime(..., tzinfo=utc)
    >>> padding  = datetime.timedelta(...)
    >>> it = baze_iterator(baze, tag, start_date, end_date, padding=padding)
    >>> for series, s, e in it:
    ...     #do something

    """

    def __init__(self, baze, tags, start=None, end=None,
                 interval=datetime.timedelta(1), padding=datetime.timedelta(0),
                 leftpad=True, rightpad=False, tag_kwargs=None):
        """
        Parameters
        ----------

        baze : camille.source.bazefetcher(root)
            The bazefetcher source function
        tag : str or list of str
            The tag the series will be written from
        start : datetime.datetime
            The start time of the data to be read (Inclusive)
            Must be timezone aware
        end : datetime.datetime
            The end time of the data to be read (Exclusive)
            Must be timezone aware
        interval : datetime.timedelta
            The interval of the iterations. Must be days. Defaults to 1
        padding : datetime.timedelta or int
            The padding that is applied to each iteration. Can be specified as
            a timedelta or number of samples (int). Defaults to 0
        leftpad : Bool
            Add the padding to the start of each iteration. Defaults to True
        rightpad : Bool
            Add the padding to the end of each iteration. Defaults to False
        tag_kwargs : dict
            Dictionary of additional key arguments to pass when running
            baze_fetcher source for the given keyword
        """

        if start is None:
            start = _find_start_time(baze, tags)
        if end is None:
            end = _find_stop_time(baze, tags)

        self.baze = baze
        self.tags = tags
        self.interval = interval
        self.padding = padding
        self.leftpad = leftpad
        self.rightpad = rightpad
        self.start = start
        self.stop = end
        periods = ceil((end - start) / interval)
        self.beg = pd.date_range(start=start, periods=periods, freq=interval)
        self.end = self.beg + interval
        self.it = list(zip(self.beg, self.end))
        self.tag_kwargs = tag_kwargs if tag_kwargs is not None else {}


    def __iter__(self):
        for b, e in self.it:
            e = min(e, self.stop)
            lrange, rrange = b, e

            if not isinstance(self.padding, int):
                if self.leftpad: lrange = b - self.padding
                if self.rightpad: rrange = e + self.padding

            if isinstance(self.tags, str):
                d = self.baze(self.tags, lrange, rrange,
                              **self.tag_kwargs.get(self.tags, {}))
            else:
                d = {t: self.baze(t, lrange, rrange,
                                  **self.tag_kwargs.get(t, {}))
                     for t in self.tags}

            if isinstance(self.padding, int):
                if isinstance(d, dict):
                    for k in d:
                        d[k] = self._index_pad(d[k], lrange, rrange, k)
                else:
                    d = self._index_pad(d, lrange, rrange, self.tags)

            yield d, b, e

    def __len__(self):
        return len(self.it)

    def _index_pad(self, series, s, e, tag):
        min_time = None
        max_time = None
        if self.leftpad:
            p = s
            while True:
                p -= datetime.timedelta(days=1)

                a = self.baze(tag, p, s, **self.tag_kwargs.get(tag, {}))
                if len(a) >= self.padding:
                    return a.iloc[-self.padding:].append(series)

                if not min_time:
                    min_time = _find_start_time(self.baze, tag)

                if min_time and p <= min_time:
                    return series

        if self.rightpad:
            p = e
            while True:
                p += datetime.timedelta(days=1)

                a = self.baze(tag, e, p, **self.tag_kwargs.get(tag, {}))
                if len(a) >= self.padding:
                    return series.append(a.iloc[:self.padding])

                if not max_time:
                    min_time = _find_stop_time(self.baze, tag)

                if max_time and p >= max_time:
                    return series


def _get_all_files(src_dirs, tags):
    tags = [tags] if isinstance(tags, str) else tags

    tag_roots = [ join(dr, tag)
                  for dr in src_dirs
                  for tag in tags
                  if isdir( join(dr, tag) ) ]

    if not tag_roots:
        msg = 'None of the tags {} were found in {}'.format(tags, src_dirs)
        raise ValueError(msg)

    fn_rgx = r'.*\.json\.gz$'
    file_names = [join(r, fn)
                  for r in tag_roots
                  for fn in os.listdir(r)
                  if re.match(fn_rgx, fn)]

    return file_names


def _find_start_time(baze, tags):
    files = _get_all_files(baze.src_dirs, tags)
    file_dates = [ _fn_start_date(fn) for fn in files ]
    return min( file_dates )


def _find_stop_time(baze, tags):
    files = _get_all_files(baze.src_dirs, tags)
    file_dates = [ _fn_end_date(fn) for fn in files ]
    return max( file_dates )
