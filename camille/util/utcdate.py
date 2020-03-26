from datetime import datetime
from pytz import utc


def utcdate(*args, **kwargs):
    """utcdate

    Make timezone aware utc datetime. Parameters are assumed to be in UTC,
    unless they already have a timezone, in which case they will be converted.

    Parameters
    ----------
    *args[0] : date-like, optional
        date-like object to be made timezone aware
    **kwargs
        datetime constructor arguments

    Returns
    -------
    datetime
        Timezone aware datetime utc
    """
    if kwargs:
        # If keyword arguments are specified, use to construct new datetime
        return utc.localize(datetime(**kwargs))

    d = args[0]

    try:
        # Try to localize the datetime-like. utc.localize will add timezone to
        # datetime without conversion.
        return utc.localize(d)
    except ValueError:
        # If the datetime-like already has a timezone, localize will raise a
        # ValueError. Convert the timezone to utc.
        return d.astimezone(utc)
    except AttributeError:
        # The given date-like is not datetime-like, construct a datetime
        return utc.localize(datetime(year=d.year, month=d.month, day=d.day))
