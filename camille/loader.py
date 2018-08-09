"""loader

Module for loading and running a yaml based workflow description.

Examples
--------

Usage:
>>> cfg = camille.load_config('my_config.yml')
>>> camille.run(cfg)

Config format:

tag: [.*HS2.*]
start: 2018-01-01
end: 2018-01-06
processor:
    fft:
        inverse: False
input:
    bazefetcher:
        base_folder: ./jc
join: outer
interpolation: nearest

"""

import yaml
import datetime
import pytz
import re
from functools import partial
from os import path

from .processors import fft, rolling
from .input_loaders import bazefetcher

_processors = {
    'fft': fft.process,
    'rolling': rolling.process
}

_input_loaders = {
    'bazefetcher': bazefetcher.load
}

def run(config):
    tag = config['tag']
    start = config['start']
    end = config['end']
    interpolation = config['interpolation']
    join = config['join']

    inp = config['input'](tag,
                            start,
                            end,
                            interpolation=interpolation,
                            join=join)

    return config['processor']( inp )

def _tag(tag):
    try:
        return [ re.compile(tag) ]
    except TypeError:
        return [ re.compile(t) for t in tag ]

def _to_datetime(time):
    # Converts to midnight datetime if given as date
    if not isinstance(time, datetime.datetime):
        time = datetime.datetime(time.year, time.month, time.day)
    try:
        return pytz.utc.localize(time)
    except ValueError:
        return time.astimezone(pytz.utc)

def _time(time):
    if isinstance(time, datetime.date):
        return _to_datetime(time)
    msg = "'{0}' is not a valid date/time".format(time)
    raise ValueError(msg)

def _processor(processor):
    try:
        return _processors[processor]
    except TypeError:
        function = list(processor.keys())[0]
        args     = list(processor.values())[0]
        return partial(_processors[function], **args)

def _input(inp):
    try:
        return _input_loaders[inp]
    except TypeError:
        function = list(inp.keys())[0]
        args     = list(inp.values())[0]
        return partial(_input_loaders[function], **args)

def load_config(config):
    """Loads a yaml config file

    Config format
    -------------
    tag : list[str]
        Filters for collecting data to be processed. Each string in the list is
        a regular expression for filtering data to populate a column in the
        dataframe to be processed.
    start : Union[date, datetime]
        Collect data from (including) this time.
    end : Union[date, datetime]
        Collect data before (not including) this time.
    processor : Union[dict, dict[dict]]
        Dict containing a processor name and an optional dict of
        keyword arguments.
    input : Union[dict, dict[dict]]
        Dict containing an input reader name and an optional dict of
        keyword arguments.
    """
    try:
        path.realpath(config)
        with open(config, 'r') as f:
            config = yaml.safe_load(f)
    except TypeError:
        pass

    return {
        'tag': _tag(config['tag']),
        'start': _time(config['start']),
        'end': _time(config['end']),
        'processor': _processor(config['processor']),
        'input': _input(config['input']),
        'join': config.get('join'),
        'interpolation': config.get('interpolation')
    }
