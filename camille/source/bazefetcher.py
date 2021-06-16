from ..util import utcdate
from abc import ABC
from abc import abstractmethod
import contextlib
import datetime
import os
import pandas as pd
import paramiko
import pathlib
import pytz
import re
import stat
import threading


class AbstractIO(ABC):
    @abstractmethod
    def __enter__(self):
        """
        Using an IO implementation as a context manager should yield an io
        object implementing an interface similar to that of `pathlib.Path`
        """

    @abstractmethod
    def __exit__(self, exc_type, exc_value, trace):
        """Close resources and forward errors"""


class RemoteIO(AbstractIO):
    class RemotePath:
        """
        Internal helper object providing an interface similar to that of
        `pathlib.Path` over ssh
        """
        def __init__(self, owner, path=None):
            self.owner = owner
            self._path = path

        def __getattr__(self, name):
            """
            RemotePath is a partial implementation of `pathlib.Path`. This
            method communicates to the caller that if the attribute `name` is
            implemented in `pathlib.Path`, there is an intention that it should
            be implemented in this class as well.

            We do however only bother to implement specifically the interface
            that is used in this module.
            """
            if hasattr(pathlib.Path, name):
                msg = f'{name} is not implemented for RemotePath'
                raise NotImplementedError(msg)
            clsname = self.__class__.__name__
            msg = f"'{clsname}' object has no attribute '{name}'"
            raise AttributeError(msg)

        @property
        def path(self):
            return self._path if self._path is not None else self.owner.path

        @property
        def name(self):
            return self.path.name

        def is_dir(self):
            try:
                remote_stat = self.owner.sftp.stat(str(self.path))
                return bool(stat.S_ISDIR(remote_stat.st_mode))
            except FileNotFoundError:
                return False

        def iterdir(self):
            return (self / f for f in self.owner.sftp.listdir(str(self.path)))

        def open(self,
                 mode='r',
                 buffering=-1,
                 encoding=None,
                 errors=None,
                 newline=None):
            return self.owner.sftp.open(str(self.path), mode)

        def _replace(self, **kwargs):
            """
            Replace the existing values of class attributes with new ones.
            Parameters
            ----------
            kwargs : dict
                keyword arguments corresponding to one or more attributes whose
                values are to be modified
            Returns
            -------
            A new class instance with replaced attributes
            """
            attribs = {k: kwargs.pop(k, v) for k, v in vars(self).items()}
            if kwargs:
                raise ValueError(f'Got unexpected field names: {list(kwargs)!r}')
            inst = self.__class__.__new__(self.__class__)
            inst.__dict__.update(attribs)
            return inst

        def __eq__(self, other):
            if self.__class__ is not other.__class__:
                return False
            return self.owner == other.owner and self.path == other.path

        def __lt__(self, other):
            if not isinstance(other, self.__class__):
                msg = (f"TypeError: '<' not supported between instances of "
                       f"'{self.__class__.__name__}' and "
                       f"'{other.__class__.__name__}'")
                raise TypeError(msg)
            return str(self) < str(other)

        def __truediv__(self, other):
            return self._replace(_path=self.path / other)

        def __repr__(self):
            return f'{self.__class__.__name__}<{str(self.path)}>'

    @staticmethod
    def parse_path(path):
        xs = str(path)
        username = None
        if '@' in path:
            username, xs = xs.split('@')
        host, p = xs.split(':', 1)
        return pathlib.Path(p), host, username

    def __init__(self, path, missing_host_key_policy=paramiko.WarningPolicy()):
        self._original_path = path
        self.path, self.host, self.username = self.parse_path(path)
        self.port = 22
        self.missing_host_key_policy = missing_host_key_policy
        self._connection = None
        self._sftp = None
        self._use_count = 0
        self._lock = threading.Lock()

    @property
    def ssh(self):
        if self._connection is None:
            raise ValueError('RemoteIO not connected')
        return self._connection

    @property
    def sftp(self):
        if self._sftp is None:
            assert self.ssh.get_transport() != None
            self._sftp = self.ssh.open_sftp()
        return self._sftp

    def _create_connection(self):
        conection = paramiko.SSHClient()
        conection.set_missing_host_key_policy(self.missing_host_key_policy)
        conection.connect(self.host,
                          port=self.port,
                          username=self.username,
                          allow_agent=False,
                          look_for_keys=True)
        return conection

    def __enter__(self):
        with self._lock:
            if self._connection is None:
                self._connection = self._create_connection()
            self._use_count += 1
        return self.RemotePath(self)

    def __exit__(self, exc_type, exc_value, trace):
        with self._lock:
            self._use_count -= 1
            if self._use_count < 0:
                raise RuntimeError('RemoteIO invariant error')
            if self._use_count == 0:
                if self._sftp is not None:
                    self._sftp.close()
                    self._sftp = None
                self._connection.close()
                self._connection = None
        if exc_type is not None:
            return False

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return False
        return self._original_path == other._original_path


class LocalIO(AbstractIO):
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        print(self.path)
        return pathlib.Path(self.path)

    def __exit__(self, exc_type, exc_value, trace):
        if exc_type is not None:
            return False

    def __repr__(self):
        return str(self.path)


class TagNotFoundError(ValueError):
    pass


date_pattern = r'[0-9]{4}-[0-9]{2}-[0-9]{2}'
time_pattern = r'[0-9]{2}\.[0-9]{2}\.[0-9]{2}\+[0-9]{2}\.[0-9]{2}'
dt_pattern = date_pattern + 'T' + time_pattern
fn_tail_pattern = '_' + dt_pattern + '_' + dt_pattern + r'\.json\.gz$'


def _fn_start_date(fn):
    # File names are on the form:
    #     |- start_date ----------| |- end_date ------------|
    # tag_YYYY-MM-DDTHH.MM.SS+HH.MM_YYYY-MM-DDTHH.MM.SS+HH.MM.json.gz
    date_str = fn.split('_')[-2] # extract start date
    date_str = date_str.replace('.', '') # UTC offset does not support '.'
    date_fmt = "%Y-%m-%dT%H%M%S%z"
    return datetime.datetime.strptime(date_str, date_fmt)


def _fn_end_date(fn):
    date_str = fn.split('_')[-1] # extract start date
    date_str = date_str.replace('.', '') # UTC offset does not support '.'
    date_fmt = "%Y-%m-%dT%H%M%S%zjsongz"
    return datetime.datetime.strptime(date_str, date_fmt)


def _tidy_frame(df, tzinfo):
    if df is None or df.empty or 't' not in df.columns:
        df.drop(df.index, inplace=True)
        df.insert(0, 't', [])
        df.insert(1, 'v', [])
    df.rename(columns={
        't': 'time',
        'v': 'value',
        }, inplace=True)

    df.time = pd.to_datetime(df.time, unit='ms')
    df.set_index('time', inplace=True)
    df.index = df.index.tz_localize(tzinfo)
    df.sort_index(inplace=True)


def _get_files(io, fn_regex, date_pred):
    """
    Gets all possible files with tag under io which satisfy
    fn_regex and date_pred
    """
    file_contexts = [f for f in io.iterdir()
                     if fn_regex.match(f.name) and date_pred(f.name)]
    return file_contexts


def _get_fn_regex(tag):
    return re.compile(re.escape(tag) + fn_tail_pattern)


def _get_files_between_start_and_end(io, tag, start_dt, end_dt):
    return _get_files(
        io,
        _get_fn_regex(tag),
        lambda fn: _fn_start_date(fn) < end_dt and _fn_end_date(fn) > start_dt
    )


def _extend_bwd(io, tag, start_date, df, fn_regex, tzinfo):
    """
    Extends the range to include the last sample before or at the same time
    as the start of time range
    """

    if df.index.min() <= start_date:
        start_date = df[:start_date].index.max()
        return df, start_date

    files = _get_files(io, fn_regex, lambda fn: _fn_end_date(fn) <= start_date)

    while True:
        if not files: break

        prev_f = max(files, key=lambda x: _fn_end_date(x.name))
        tmp_df = pd.read_json(prev_f, compression='gzip')

        if tmp_df.empty:
            files.remove(prev_f)
            continue

        _tidy_frame(tmp_df, tzinfo)

        start_date = tmp_df.index.max()

        df.loc[start_date] = tmp_df.loc[start_date]
        df.sort_index(inplace=True)
        break

    return df, start_date


def _extend_fwd(io, tag, end_date, df, fn_regex, tzinfo):
    """
    Extends the range to include the next sample after or at the same time
    as the end of time range
    """

    if df.index.max() >= end_date:
        end_date = df[end_date:].index.min()
        return df, end_date + datetime.timedelta(microseconds=1)

    files = _get_files(io, fn_regex, lambda fn: _fn_start_date(fn) >= end_date)

    while True:
        if not files: break

        next_f = min(files, key=lambda x: _fn_start_date(x.name))
        tmp_df = pd.read_json(next_f, compression='gzip')

        if tmp_df.empty:
            files.remove(next_f)
            continue

        _tidy_frame(tmp_df, tzinfo)

        end_date = tmp_df.index.min()

        df.loc[end_date] = tmp_df.loc[end_date]
        df.sort_index(inplace=True)
        end_date += datetime.timedelta(microseconds=1)
        break

    return df, end_date


class Bazefetcher:
    """Bazefetcher

    Callable object that can be used to read time series from specified root
    paths. Tag split across paths is supported as long as all filenames are
    unique. Paths are given in the following format:
        `[<user>@<host>:]<posix-path>`
    Paths will be considered remote if they contain ':'.

    Attributes
    ----------
    src_dir : str or iterable of str
        Path to the bazefetcher root directories
    tzinfo :datetime.tzinfo
        Time series timezone

    Examples
    --------

    Read time series `series` with tag `tag`:

    >>> start_date = datetime.datetime(2029, 1, 1, tzinfo=pytz.utc)
    >>> end_date = datetime.datetime(2030, 1, 1, tzinfo=pytz.utc)
    >>> cin = camille.source.Bazefetcher('<root-directory>')
    >>> ts = cin('tag', start_date, end_date)

    >>> cin = camille.source.Bazefetcher(
    ...           ['tests/test_data/baze', 'tests/test_data/authored'])
    >>> ts = cin('Perlin', start_date, end_date, snap='both')
    """

    def __init__(self, path=None, paths=None, tzinfo=pytz.utc):
        if path is None and paths is None or (
            path is not None and paths is not None):
            raise ValueError('specify either path or paths')
        if path is not None:
            if not isinstance(path, str):
                raise TypeError(f'Expected str type, not {type(path)}')
            paths = [path]
        self.srcs = [
            self._select_protocol(path)
            for path in paths
        ]
        self.tzinfo = tzinfo

    @staticmethod
    def _select_protocol(path):
        if os.name == 'nt':
            drive, xs = os.path.splitdrive(path)
            xs = xs.split(':', 1)
            if len(xs) == 2:
                return RemoteIO(path)
        elif ':' in path:
            return RemoteIO(path)

        return LocalIO(path)

    @contextlib.contextmanager
    def _tag_protocol(self, tag):
        protocols = iter(self.srcs)
        while True:
            try:
                protocol = next(protocols)
                with protocol as io:
                    io = io / tag
                    if io.is_dir():
                        yield io
                        break
            except StopIteration:
                msg = f'Tag {tag} not found in {self.srcs}'
                raise TagNotFoundError(msg)

    def __call__(self,
                 tag,
                 start_date=utcdate(year=1677, month=9, day=22),
                 end_date=utcdate(year=2262, month=4, day=11),
                 snap=None):
        """
        Parameters
        ----------
        tag : str
            The tag of the series to read
        start : datetime.datetime
            The start time of the data to be read. Must be timezone aware
        end : datetime.datetime
            The end time of the data to be read. Must be timezone aware
        snap : str
            'left', 'right' or 'both' (default None).
            Direction in which returned data should be extended

        Returns
        -------
        pandas.TimeSeries
            Loaded time series
        """
        if start_date.tzinfo is None or end_date.tzinfo is None:
            raise ValueError('dates must be timezone aware')

        if not start_date <= end_date:
            raise ValueError('start_date must be earlier than end_date')

        with self._tag_protocol(tag) as io:
            files = _get_files_between_start_and_end(io,
                                                     tag,
                                                     start_date,
                                                     end_date)
            with contextlib.ExitStack() as exit_stack:
                L = [
                    pd.read_json(buffer, compression='gzip') for buffer in (
                        exit_stack.enter_context(f.open(mode='rb'))
                        for f in files
                    )
                ]
            df = pd.concat(L, sort=True) if len(L) > 0 else pd.DataFrame()

            _tidy_frame(df, self.tzinfo)
            fn_regex = _get_fn_regex(tag)

            if snap == 'left' or snap == 'both':
                df, start_date = _extend_bwd(io,
                                             tag,
                                             start_date,
                                             df,
                                             fn_regex,
                                             self.tzinfo)

            if snap == 'right' or snap == 'both':
                df, end_date = _extend_fwd(io,
                                           tag,
                                           end_date,
                                           df,
                                           fn_regex,
                                           self.tzinfo)

        try:
            eps = datetime.timedelta(microseconds=1)
            ts = df.value
            ts = ts[start_date:end_date - eps]
        except KeyError:
            pass

        return ts
