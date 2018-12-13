import os
import datetime
import pytz
import pandas as pd
from camille.source.bazefetcher import _safe_read, _tidy_frame


def _to_midnight_utc(timestamp):
    """ Copied from bazefetcher, logic modified

    Converts a timestamp to an UTC timestamp, to midnight of the
    given date (00:00:00). All timestamps are converted to UTC if they
    have timezone information, and assumed to already be UTC if they
    have no timezone information.
    """
    try:
        timestamp = pytz.utc.localize(timestamp)
    except ValueError:
        timestamp = timestamp.astimezone(pytz.utc)
    timestamp = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    return timestamp


def _daterange(start_date, end_date):
    """
    Generates dates in range between start_date and end_date with one
    day difference starting from start_date.
    First calls _to_midnight_utc on both.
    :param start_date: Start date timestamp, inclusive.
    :param end_date: End date timestamp, exclusive. Note, that if end
    time date is later than midnight of that day, the midnight date
    will be generated. If the date is exactly at midninght,
    it's not generated
    :return:
    """
    if start_date != end_date:
        is_end_on_midnight = _to_midnight_utc(end_date) == end_date
        start_date = _to_midnight_utc(start_date)
        end_date = _to_midnight_utc(end_date)
        if is_end_on_midnight:
            end_date -= datetime.timedelta(days=1)
        while start_date <= end_date:
            next_day = start_date + datetime.timedelta(days=1)
            yield (start_date, next_day)
            start_date = next_day


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


def _merge(ts, into, overwrite=False):
    into_start, into_end = min(into.index), max(into.index)
    ts_start, ts_end = min(ts.index), max(ts.index)

    overlap = into_start <= ts_end and into_end >= ts_start

    if overlap and not overwrite:
        msg = (
            'you are attempting to write data for a time interval'
            ' that already exists. Set overwrite=True to overwrite.'
        )
        raise ValueError(msg)

    eps = datetime.timedelta(microseconds=1)
    ts = pd.concat([into.value[ts_end+eps:], ts, into.value[:ts_start-eps]])

    return ts


def bazefetcher(root):
    """Bazefetcher

    Creates a function that can be used to write time series' to the specified
    root directory

    Parameters
    ----------
    root : str or path-like
        Path to the bazefetcher root directory

    Returns
    -------
    function (pandas.Series, str, datetime.datetime, datetime.datetime, bool)
        Function for writing time series' to the bazefetcher root directory
            series : pandas.Series
                Time series to write. The time series index must be timezone
                aware
            tag : str
                The tag the series will be written to
            start : datetime.datetime, optional
                The start time of the data to be written. Must be
                timezone aware. Default is None, which implies series start
            end : datetime.datetime, optional
                The end time of the data to be written. Must be
                timezone aware. Default is None, which implies series end
            overwrite : bool, optional
                True - existing data, which overlaps with the data
                to be written, is deleted.
                False - raise a ValueError on overwrite attempt.
                Default is False

    Examples
    --------

    Write time series `series` to tag `tag`:

    >>> start_date = datetime.datetime(2029, 1, 1, tzinfo=pytz.utc)
    >>> end_date = datetime.datetime(2030, 1, 1, tzinfo=pytz.utc)
    >>> cout = camille.output.bazefetcher('<root-directory>')
    >>> cout(series, tag, start_date, end_date)

    Write series to file with existing data:

    >>> start_date = datetime.datetime(2018, 1, 1, 13, tzinfo=pytz.utc)
    >>> end_date = datetime.datetime(2018, 1, 1, 16, tzinfo=pytz.utc)
    >>> cin = camille.source.bazefetcher('<root-directory>')
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
    >>> cout = camille.output.bazefetcher('<root-directory>')
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
    if not os.path.isdir(root):
        raise ValueError('{} is not a directory'.format(root))

    def bazefetcher_internal(
            series, tag=None, start=None, end=None, overwrite=False):
        """
        See Also
        --------
        bazefetcher
        """
        if tag is None:
            raise ValueError('tag must be specified')

        eps = datetime.timedelta(microseconds=1)
        if start is None: start = series.index[0].to_pydatetime()
        if end is None: end = series.index[-1].to_pydatetime() + eps

        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError('dates must be timezone aware')

        if not start <= end:
            raise ValueError('start_date must be earlier than end_date')

        series = series[start:end-eps]

        for s, e in _daterange( start, end ):
            tag_path = _generate_tag_location( root,
                                               tag,
                                               s,
                                               e,
                                               full_path=True,
                                               suffix='.json.gz' )

            ts = series[s:e-eps]
            if ts.empty: continue

            if not os.path.exists(os.path.dirname(tag_path)):
                try:
                    os.makedirs(os.path.dirname(tag_path))
                except OSError as exc: # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise

            file_content = _safe_read(tag_path)
            _tidy_frame(file_content, tzinfo=pytz.utc)
            if not file_content.empty:
                ts = _merge(ts, into=file_content, overwrite=overwrite)

            ts = pd.DataFrame( { 't':ts.index, 'v':ts.values } )
            ts.to_json(tag_path, compression='gzip', orient='records' )

    return bazefetcher_internal
