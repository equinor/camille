import os
import datetime
import pytz


def bazefetcher(root, tzinfo=pytz.utc):
    if not os.path.isdir(root):
        raise ValueError('{} is not a directory'.format(root))

    if not isinstance(tzinfo, datetime.tzinfo):
        raise ValueError('tzinfo must be instance of datetime.tzinfo')

    def to_midnight_utc(timestamp):
        """ Copied from bazefetcher

        Converts a timestamp or date to an UTC timestamp. Dates are converted to midnight the given date (00:00:00).
        All timestamps are converted to UTC if they have timezone information, and assumed to already be UTC if they have no
         timezone information. """
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

    def generate_tag_location(tag_name, start_date, end_date, full_path=True, suffix=".json"):
        """ Copied from bazefetcher

        Generates and returns the path for storing a tag given a start and end date. With full_path=False it will
        return the relative path to the storage driver location
         """
        filename = "{}_{}_{}{}".format(
            tag_name,
            to_midnight_utc(start_date).isoformat().replace(":", "."),
            to_midnight_utc(end_date).isoformat().replace(":", "."),
            suffix)
        directory_name = tag_name
        path = os.path.join(directory_name, filename)
        if full_path:
            path = os.path.join(root, path)
        return path

    def bazefetcher_internal(
        tag, start_date, end_date, series,
        ):
        if start_date.tzinfo is None or end_date.tzinfo is None:
            raise ValueError('dates must be timezone aware')

        if not start_date <= end_date:
            raise ValueError('start_date must be earlier than end_date')

        tag_path = generate_tag_location(
            tag, start_date, end_date, full_path=False, suffix='.json.gz')

        s = series.copy()
        s.name = 'v'
        s.index.name = 't'
        s.to_json(tag_path, compression='gzip')
