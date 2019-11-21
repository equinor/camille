from camille.source.bazefetcher import _tidy_frame
import datetime
import errno
import os
import pandas as pd
import pytz


def _generate_tag_location(
    root, tag_name, start_date, end_date, full_path=True, suffix=".json"
    ):
    """ Copied from bazefetcher, logic modified

    Generates and returns the path for storing a tag given a start and end
    date. With full_path=False it will return the relative path to the
    storage driver location
     """
    filename = "{}_{}_{}{}".format(
        tag_name,
        start_date.isoformat().replace(":", "."),
        end_date.isoformat().replace(":", "."),
        suffix)
    directory_name = tag_name
    path = os.path.join(directory_name, filename)
    if full_path:
        path = os.path.join(root, path)
    return path


def _merge(ts, into, overwrite=False, fill=False):
    into_start, into_end = min(into.index), max(into.index)
    ts_start, ts_end = min(ts.index), max(ts.index)

    overlap = into_start <= ts_end and into_end >= ts_start

    if not overlap or overwrite:
        eps = datetime.timedelta(microseconds=1)
        ts = pd.concat([
            into.value[:ts_start - eps],
            ts,
            into.value[ts_end + eps:]
        ])
    elif fill:
        idx = ~ts.index.isin(into.index)
        ts = pd.concat([into.value, ts[idx]]).sort_index()
    else:
        msg = (
            'you are attempting to write data for a time interval'
            ' that already exists. Set either overwrite=True or fill=True, to'
            ' overwrite interval, or fill in missing.'
        )
        raise ValueError(msg)

    return ts


class Bazefetcher:
    """Bazefetcher

    Creates a callable object that can be used to write time series' to the
    specified root directory

    Parameters
    ----------
    root : str or path-like
        Path to the bazefetcher root directory

    Examples
    --------

    Write time series `series` to tag `tag`:

    >>> start_date = datetime.datetime(2029, 1, 1, tzinfo=pytz.utc)
    >>> end_date = datetime.datetime(2030, 1, 1, tzinfo=pytz.utc)
    >>> cout = camille.output.Bazefetcher('<root-directory>')
    >>> cout(series, tag, start_date, end_date)

    Write series to file with existing data:

    >>> start_date = datetime.datetime(2018, 1, 1, 13, tzinfo=pytz.utc)
    >>> end_date = datetime.datetime(2018, 1, 1, 16, tzinfo=pytz.utc)
    >>> cin = camille.source.Bazefetcher('<root-directory>')
    >>> ts = cin('tag', start_date, end_date)
    >>> #print existing data
    >>> ts
    time
    2018-01-01 13:00:00+00:00    11
    2018-01-01 14:00:00+00:00    22
    2018-01-01 15:00:00+00:00    33
    Name: value, dtype: int64
    >>> series
    2018-01-01 14:00:00+00:00    66
    2018-01-01 15:00:00+00:00    77
    2018-01-01 16:00:00+00:00    88
    2018-01-01 17:00:00+00:00    99
    dtype: int64
    >>> cout = camille.output.Bazefetcher('<root-directory>')
    >>> cout(series, 'tag', overwrite = True)
    >>> end_date = datetime.datetime(2018, 1, 1, 18, tzinfo=pytz.utc)
    >>> ts = cin('tag', start_date, end_date)
    >>> #print updated data
    >>> ts
    time
    2018-01-01 13:00:00+00:00    11
    2018-01-01 14:00:00+00:00    66
    2018-01-01 15:00:00+00:00    77
    2018-01-01 16:00:00+00:00    88
    2018-01-01 17:00:00+00:00    99
    Name: value, dtype: int64
    """

    def __init__(self, root, tzinfo=pytz.utc):

        if not os.path.isdir(root):
            raise ValueError('{} is not a directory'.format(root))

        if not isinstance(tzinfo, datetime.tzinfo):
            raise ValueError('tzinfo must be instance of datetime.tzinfo')

        self.root = root
        self.tzinfo = tzinfo

    def __call__(self,
                 series,
                 tag,
                 start=None,
                 end=None,
                 overwrite=False,
                 fill=False):
        """
        Parameters
        ----------
        series : pandas.Series
            Time series to write. The time series index must be timezone
            aware
        tag : str
            The tag of the series to read
        start : datetime.datetime
            The start time of the data to be read. Must be timezone aware
        end : datetime.datetime
            The end time of the data to be read. Must be timezone aware
        overwrite : bool, optional
            True - existing data, which overlaps with the data
            to be written, is deleted.
            False - raise a ValueError on overwrite attempt.
            Default is False
        fill : bool, optional
            True - existing timestamps are kept, new are inserted
            False - raise a ValueError on overwrite attempt.
            Default is False
        """

        if tag is None:
            raise ValueError('tag must be specified')

        if series.empty:
            return

        eps = datetime.timedelta(microseconds=1)
        if start is None: start = series.index[0].to_pydatetime()
        if end is None: end = series.index[-1].to_pydatetime() + eps

        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError('dates must be timezone aware')

        if not start <= end:
            raise ValueError('start_date must be earlier than end_date')

        series = series[start:end-eps].tz_convert(pytz.utc)

        for d, view in series.groupby(series.index.date):
            s = datetime.datetime(d.year, d.month, d.day, tzinfo=pytz.utc)
            e = s + datetime.timedelta(days=1)
            tag_path = _generate_tag_location(self.root,
                                              tag,
                                              s,
                                              e,
                                              full_path=True,
                                              suffix='.json.gz')

            if not os.path.exists(os.path.dirname(tag_path)):
                try:
                    os.makedirs(os.path.dirname(tag_path))
                except OSError as exc: # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise

            try:
                old = pd.read_json(tag_path)
            except (FileNotFoundError,
                    ValueError,
                    pd.errors.EmptyDataError):
                old = pd.DataFrame()

            _tidy_frame(old, tzinfo=pytz.utc)
            if not old.empty:
                view = _merge(view, into=old, overwrite=overwrite, fill=fill)

            view = pd.DataFrame({'t': view.index, 'v': view.values})
            view.to_json(tag_path, compression='gzip', orient='records')
