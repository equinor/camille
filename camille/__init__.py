"""Camille is a timeseries processing toolbox.

"""

try:
    import pkg_resources
    __version__ = pkg_resources.get_distribution(__name__).version
except pkg_resources.DistributionNotFound:
    pass

from . import output, process, source, util

__all__ = [
    'output',
    'process',
    'source',
    'util',
]
