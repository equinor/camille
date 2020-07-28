from io import StringIO
from pytz import utc
from subprocess import PIPE
from subprocess import Popen
import pandas as pd
import requests


urljoin = requests.compat.urljoin
default_host='https://resource-zephyre-dev.playground.radix.equinor.com:443'


def isoformat(date):
    if date.tzinfo != utc:
        raise ValueError('Dates must be UTC')
    date = date.replace(tzinfo=None)
    return date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def parse_response(strio, tzinfo=utc):
    df = pd.read_json(strio, orient='records')

    if df is None or df.empty or 'time' not in df.columns:
        df.drop(df.index, inplace=True)
        df.insert(0, 'time', [])
        df.insert(1, 'value', [])

    df.value = pd.to_numeric(df.value)
    df.time = pd.to_datetime(df.time)
    df.set_index('time', inplace=True)
    df.index = df.index.tz_localize(tzinfo)
    df.sort_index(inplace=True)

    return df.value


class Zephyre:
    """Zephyre

    Callable object that can be used to fetch time series from zephyre service.

    Notes
    -----
    `oauth2local serve` must be running in order to authenticate with the
    zephyre API.

    Examples
    --------
    Fetch time series named `tag`:

    >>> start_date = utcdate(year=2019, month=1, day=1)
    >>> end_date = utcdate(year=2019, month=1, day=1)
    >>> z = Zephyre()
    >>> ts = z('tag', start_date, end_date, snap='both')
    """

    def __init__(self, host=default_host):
        self.host = host

    def _get_token(self):
        proc = Popen(['oauth2local', 'token'], stdin=PIPE, stdout=PIPE)
        out, err = proc.communicate()
        exit_code = proc.wait(timeout=0.005)

        if exit_code == 8:
            msg = 'oauth2local could not be reached, is it running?'
            raise RuntimeError(msg)
        elif exit_code != 0:
            msg = 'oauth2local token non zero exit code {}, {}, {}'
            raise RuntimeError(msg.format(exit_code, out, err))

        return out.decode('utf-8').strip()

    @property
    def token(self):
        return self._get_token()


    def __call__(self, tag, start_date, end_date, tzinfo=utc):
        """
        Parameters
        ----------
        tag : str
            The tag of the series to fetch
        start_date : datetime.datetime
            The start time of the data to be read. Must be timezone aware
        end_date : datetime.datetime
            The end time of the data to be read. Must be timezone aware

        Returns
        -------
        pandas.TimeSeries
            Fetched time series
        """
        if start_date.tzinfo is None or end_date.tzinfo is None:
            raise ValueError('dates must be timezone aware')

        if not start_date <= end_date:
            raise ValueError('start_date must be earlier than end_date')

        url = urljoin(self.host, 'timeseries')

        headers = {
            'Authorization': 'Bearer {}'.format(self.token),
        }
        params = {
            'measurementName': tag,
            'start': isoformat(start_date),
            'end': isoformat(end_date),
        }
        resp = requests.get(url, params=params, headers=headers, stream=True)
        resp.raise_for_status()

        with StringIO() as strio:
            for data in resp.iter_content(chunk_size=8192):
                s = data.decode('utf-8')
                strio.write(s)
            strio.seek(0)
            return parse_response(strio)
