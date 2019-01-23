#!/usr/bin/env python3
import pandas as pd
from datetime import timedelta, time
import os
from os.path import isdir, join
from camille.source.bazefetcher import _fn_start_date, _fn_end_date
import re
from math import ceil
from collections import abc


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

    def __init__(self, baze, tags, start=None, stop=None, interval=timedelta(1),
                 padding=timedelta(0), leftpad=True, rightpad=False,
                 tag_kwargs=None):
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
        tag_kwargs : dict
            Dictionary of additional key arguments to pass when running
            baze_fetcher source for the given keyword
        """

        if start is None:
            start = _find_start_time(baze, tags)
        if stop is None:
            stop = _find_stop_time(baze, tags)

        self.baze = baze
        self.tags = tags
        self.interval = interval
        self.padding = padding
        self.leftpad = leftpad
        self.rightpad = rightpad
        self.start = start
        self.stop = stop
        periods = ceil((stop - start) / interval)
        self.beg = pd.date_range(start=start, periods=periods, freq=interval)
        self.end = self.beg + interval
        self.it = list(zip(self.beg, self.end))
        self.tag_kwargs = tag_kwargs if tag_kwargs is not None else {}


    def __iter__(self):
        for b, e in self.it:
            e = min(e, self.stop)
            lrange, rrange = b, e
            if self.leftpad: lrange = b - self.padding
            if self.rightpad: rrange = e + self.padding

            if isinstance(self.tags, str):
                d = self.baze(self.tags, lrange, rrange,
                              **self.tag_kwargs.get(self.tags, {}))
            else:
                d = {t: self.baze(t, lrange, rrange,
                                  **self.tag_kwargs.get(t, {}))
                     for t in self.tags}

            yield d, b, e

    def __len__(self):
        return len(self.it)


def _get_files(src_dirs, tags):
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
    files = _get_files(baze.src_dirs, tags)
    file_dates = [ _fn_start_date(fn) for fn in files ]
    return min( file_dates )


def _find_stop_time(baze, tags):
    files = _get_files(baze.src_dirs, tags)
    file_dates = [ _fn_end_date(fn) for fn in files ]
    return max( file_dates )
