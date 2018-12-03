"""Camille is a timeseries processing toolbox.

"""

try:
    import pkg_resources
    __version__ = pkg_resources.get_distribution(__name__).version
except pkg_resources.DistributionNotFound:
    pass

from . import process, util, output, source

__all__ = [
    'process',
    'util',
    'output',
    'source',
]
