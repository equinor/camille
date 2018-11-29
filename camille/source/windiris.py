import sqlite3
import os
import pandas as pd

def _sqlite(start_date, end_date, connection, installation):
    query = (
        'SELECT * FROM ' + installation + #nosec
        ' WHERE Timestamp >= :start AND Timestamp < :end ;'
    )

    df = pd.read_sql_query(query, connection,
                           params={
                                'start': str(start_date.replace(tzinfo=None)),
                                'end': str(end_date.replace(tzinfo=None))
                           },
                           index_col='Timestamp',
                           parse_dates={
                                'Timestamp': {'utc': True}
                           }).sort_index()

    return df


def windiris(root):
    def windiris_internal(installation, start_date, end_date):
        f = os.path.join(root, installation, installation + '_rtd.db' )
        conn = sqlite3.connect(f)

        return _sqlite(start_date, end_date, conn, installation)

    return windiris_internal
