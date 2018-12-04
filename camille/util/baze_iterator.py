#!/usr/bin/env python3
import pandas as pd
from datetime import timedelta, time


def baze_iterator(baze, tag, start, stop, interval=timedelta(1), padding=timedelta(0), leftpad=True, rightpad=False):
    """ Bazefetcher iterator

    Creates pandas.Series from camille.source.bazefetcher() as iterations of the
    time range [start, stop> at given intervals. Returns the Pandas.Series,
    start, stop for each iteration. The timerange for the returned Pandas.Series
    includes (optional) padding, while the start and stop does not.


    Parameters
    ----------

    baze : camille.source.bazefetcher(root)
        The bazefetcher source function
    tag : str
        The tag the series will be written from
    start : datetime.datetime
        The start time of the data to be read (Inclusive)
        Must be timezone aware
    stop : datetime.datetime
        The start time of the data to be read (Exclusive)
        Must be timezone aware
    interval : datetime.timedelta
        The interval of the iterations. Must be days. Defaults to 1
    padding : datetime.timedelta
        The padding that is applied to each iteration. Defaults to 0
    leftpad : Bool
        Add the padding to the start of each iteration. Defaults to True
    rightpad : Bool
        Add the padding to the end of each iteration. Defaults to False

    Returns
    -------

    data : list of pandas.Series
        The series gathered from the baze-function for each iteration.
        Includes padding
    start : list of datetime.datetime
        The start dates for all iterations. Does not include padding
    end : list of datetime.datetime
        The end time for all iterations. Does not include padding

    Raises
    ------
    ValueError
        If start dates are not at midnight or timedelta is not in days.

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
    >>> for series, s, e in baze_iterator(baze, tag, start_date, end_date, padding=padding):
    ...     #do something

    """
    _check_time(start)
    _check_time(stop)
    _check_timedelta(interval)

    beg = pd.date_range(start, stop - interval, freq=interval)
    end = pd.date_range(start + interval, stop, freq=interval)

    for b, e in zip(beg, end):
        lrange, rrange = b, e
        if leftpad: lrange = b - padding
        if rightpad: rrange = e + padding
        yield baze(tag, lrange, rrange), b, e


def _check_time(dt):
    errormsg = "Both start and stop date must start at midnight"
    if dt.time() != time(0,0):
        raise ValueError(errormsg)


def _check_timedelta(td):
    errormsg = "Interval must be in day(s)"
    if td.microseconds != 0 or td.seconds != 0:
        raise ValueError(errormsg)
