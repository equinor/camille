from camille.source import Bazefetcher
from camille.source import Zephyre
from camille.util import utcdate
from io import StringIO
from unittest.mock import patch
import datetime
import pandas as pd
import requests


bz = Bazefetcher('tests/test_data/baze')


date_fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
def parse_date(str): return utcdate(datetime.datetime.strptime(str, date_fmt))
def format_date(date): return datetime.datetime.strftime(date, date_fmt[:-1])


def jsonify(tag, start_date, end_date):
    ts = bz(tag, start_date, end_date)
    with StringIO() as out:
        df = ts.to_frame()
        df['time'] = df.index.map(format_date)
        df['quality'] = 192
        df.to_json(out, orient='records')
        return out.getvalue().encode('utf-8')


class MockResponse:
    def __init__(self, tag, start_date, end_date, status_code):
        self.json_bytes = jsonify(tag, start_date, end_date)
        print(self.json_bytes[:4096])
        self.status_code = status_code

    def raise_for_status(self):
        if (self.status_code != 200):
            raise requests.HTTPError('Mock error')

    def iter_content(self, chunk_size):
        for i in range(0, len(self.json_bytes), chunk_size):
            yield self.json_bytes[i:i + chunk_size]

# This method will be used by the mock to replace requests.get
def requests_get_mock(url, params={}, headers={}, stream=False):
    assert headers['Authorization'] == 'Bearer token'
    assert stream
    assert 'measurementName' in params
    assert 'start' in params
    assert 'end' in params

    start = parse_date(params['start'])
    end = parse_date(params['end'])
    tag = params['measurementName']

    return MockResponse(tag, start, end, 200)


def test_Zephyre_source():
    start_date = utcdate(year=2030, month=1, day=1)
    end_date = utcdate(year=2030, month=1, day=2)

    z = Zephyre()

    with patch(
        'camille.source.zephyre.Zephyre._get_token', return_value='token'
    ), patch(
        'camille.source.zephyre.requests.get',
        side_effect=requests_get_mock,
    ):
        result = z('Sin-T60s-SR01hz', start_date, end_date)
    reference = bz('Sin-T60s-SR01hz', start_date, end_date)

    pd.testing.assert_series_equal(result, reference)
