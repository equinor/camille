from databricks import sql
import keyring
from keyrings.alt.file import PlaintextKeyring
import pandas as pd
from pytz import utc

default_host = "adb-4244953073543257.17.azuredatabricks.net"
default_path = "sql/protocolv1/o/4244953073543257/0120-144726-niche729"


def isoformat(date):
    if date.tzinfo != utc:
        raise ValueError('Dates must be UTC')
    date = date.replace(tzinfo=None)
    return date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def parse_response(df, tzinfo=utc):
    df.value = pd.to_numeric(df.value)
    df.time = pd.to_datetime(df.time, errors='coerce')
    df.set_index('time', inplace=True)
    df.index = df.index.tz_localize(tzinfo)
    df.sort_index(inplace=True)

    return df.value


class OmniaDatabricks:
    """OmniaDatabricks
    Callable object that can be used to fetch time series from bf2o Databricks
    Notes
    -----
    import keyring
    from keyrings.alt.file import PlaintextKeyring as kr
    keyring.set_keyring(kr())
    keyring.set_password('bf2o_token', 'token', '<YOUR-TOKEN>') # must be set

    Examples
    --------
    Fetch time series named `tag`:
    >>> start_date = utcdate(year=2019, month=1, day=1)
    >>> end_date = utcdate(year=2019, month=1, day=2)
    >>> db = OmniaDatabricks()
    >>> ts = db('tag', start_date, end_date)
    """

    def __init__(self, host=default_host, path=default_path):
        self.host = host
        self.path = path

    def _get_token(self):
        try:
            keyring.set_keyring(PlaintextKeyring())
            token = keyring.get_password('bf2o_token', username='token')
        except Exception as ex:
            raise RuntimeError(str(ex))

        return token

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

        with sql.connect(server_hostname=self.host,
                         http_path=self.path,
                         access_token=self.token,
                         use_inline_params=True) as connection:

            with connection.cursor() as cursor:
                # Query for measurement ID
                cursor.columns(table_name="measurement_meta_table")
                query_measurement_id = '''
                SELECT
                    m.measurementId
                FROM
                    measurement_meta_table m
                WHERE
                    m.measurementName = %(tag)s
                '''
                cursor.execute(query_measurement_id, {'tag': tag})
                result = cursor.fetchall()
                measurement_id = result[0]['measurementId']

                # Query the tag data
                query_measurements = '''SELECT
                    cast(time as string) as t,
                    q,
                    cast(v as double) v
                FROM
                    measurement_data_table ts
                WHERE
                    ts.measurementId = %(measurement_id)s
                    and %(start_date)s <= ts.time and ts.time < %(end_date)s
                ORDER BY t
                '''
                cursor.execute(query_measurements, {
                    'start_date': start_date, 'end_date': end_date,
                    'measurement_id': measurement_id})
                data = pd.DataFrame(cursor.fetchall(),
                                    columns=['time', 'quality', 'value'])
                return parse_response(data)
