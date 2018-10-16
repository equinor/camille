import os
import datetime
import pytz
import pandas as pd

def _to_midnight_utc(timestamp):
    """ Copied from bazefetcher

    Converts a timestamp or date to an UTC timestamp. Dates are converted to
    midnight the given date (00:00:00).
    All timestamps are converted to UTC if they have timezone information,
    and assumed to already be UTC if they have no timezone information.
    """
    if (isinstance(timestamp, datetime.date)
        and not isinstance(timestamp, datetime.datetime)):
        timestamp = datetime.datetime(
            timestamp.year,
            timestamp.month,
            timestamp.day)
    try:
        timestamp = pytz.utc.localize(timestamp)
    except ValueError:
        timestamp = timestamp.astimezone(pytz.utc)
    return timestamp


def _daterange(start_date, end_date):
    start_date = _to_midnight_utc( start_date.date() )
    end_date = _to_midnight_utc( end_date.date() )

    for d in range(int((end_date - start_date).days)+1):
        start = start_date + datetime.timedelta(d)
        end = start + datetime.timedelta(1)
        yield (start,end)


def _generate_tag_location(
    root, tag_name, start_date, end_date, full_path=True, suffix=".json"
    ):
    """ Copied from bazefetcher

    Generates and returns the path for storing a tag given a start and end
    date. With full_path=False it will return the relative path to the
    storage driver location
     """
    filename = "{}_{}_{}{}".format(
        tag_name,
        _to_midnight_utc(start_date).isoformat().replace(":", "."),
        _to_midnight_utc(end_date).isoformat().replace(":", "."),
        suffix)
    directory_name = tag_name
    path = os.path.join(directory_name, filename)
    if full_path:
        path = os.path.join(root, path)
    return path


def bazefetcher(root):
    if not os.path.isdir(root):
        raise ValueError('{} is not a directory'.format(root))

    def bazefetcher_internal(
        series, tag=None, start=None, end=None
        ):
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError('dates must be timezone aware')

        if not start <= end:
            raise ValueError('start_date must be earlier than end_date')

        series = series[start:end]

        eps = datetime.timedelta(microseconds=1)

        for s, e in _daterange( start, end ):

            tag_path = _generate_tag_location( root,
                                              tag,
                                              s,
                                              e,
                                              full_path=True,
                                              suffix='.json.gz' )

            ts = series[s:e-eps]
            ts = pd.DataFrame( { 't':ts.index, 'v':ts.values } )

            if not os.path.exists(os.path.dirname(tag_path)):
                try:
                    os.makedirs(os.path.dirname(tag_path))
                except OSError as exc: # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise

            ts.to_json(tag_path, compression='gzip', orient='records' )

    return bazefetcher_internal
