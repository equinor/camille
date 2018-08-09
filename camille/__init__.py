"""Camille is a timeseries processing toolbox.

"""

from __future__ import absolute_import

from .processors import fft
from .processors import rolling

from .loader import load_config
from .loader import run

__version__ = '0.0.1'
