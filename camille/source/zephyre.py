from azure.identity import AzureCliCredential
from io import StringIO
from pytz import utc
import pandas as pd
import requests


urljoin = requests.compat.urljoin
default_host='https://resource-zephyre-dev.playground.radix.equinor.com:443'
default_scope = 'api://d87a78b5-431d-43a3-902a-8fc97e357395'


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
    `az login` must be run called (and succesfully finished) in order
    to authenticate with the zephyre API.

    Examples
    --------
    Fetch time series named `tag`:

    >>> start_date = utcdate(year=2019, month=1, day=1)
    >>> end_date = utcdate(year=2019, month=1, day=1)
    >>> z = Zephyre()
    >>> ts = z('tag', start_date, end_date, snap='both')
    """

    def __init__(self, host=default_host, scope=default_scope):
        self.host = host
        self.scope = default_scope

    def _get_token(self):
        try:
            credential = AzureCliCredential()
            azureToken = credential.get_token(self.scope)
        except Exception as ex:
            raise RuntimeError(str(ex))

        return azureToken.token

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
