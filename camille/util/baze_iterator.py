#!/usr/bin/env python3
import pandas as pd
from datetime import timedelta, time
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

    data : list of pandas.Series
        The series gathered from the baze-function for each iteration.
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
                 padding=timedelta(0), leftpad=True, rightpad=False, **kwargs):
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
        """



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
        self.kwargs = kwargs


    def __iter__(self):
        for b, e in self.it:
            e = min(e, self.stop)
            lrange, rrange = b, e
            if self.leftpad: lrange = b - self.padding
            if self.rightpad: rrange = e + self.padding

            if isinstance(self.tags, str):
                d = self.baze(self.tags, lrange, rrange, **self.kwargs)
            else:
                d = {t: self.baze(t, lrange, rrange, **self.kwargs)
                     for t in self.tags}

            yield d, b, e

    def __len__(self):
        return len(self.it)
