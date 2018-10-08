import pandas as pd

def windiris(root, tzinfo=pytz.utc):
    if not os.path.isdir(root):
        raise ValueError('{} is not a directory'.format(root))

    if not isinstance(tzinfo, datetime.tzinfo):
        raise ValueError('tzinfo must be instance of datetime.tzinfo')

    def windiris_internal(start_date, end_date):
        if start_date.tzinfo is None or end_date.tzinfo is None:
            raise ValueError('dates must be timezone aware')

        if not start_date <= end_date:
            raise ValueError('start_date must be earlier than end_date')

    return windiris_internal
