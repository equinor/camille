"""\
Processors
==========
This module is a collection of data processing functions. A processing function
typically takes a series and returns a processed series.

Available processors
--------------------
* :func:`~camille.process.atm_stb`
* :func:`~camille.process.delta_temp`
* :func:`~camille.process.fft`
* :func:`~camille.process.lidar`
* :func:`~camille.process.low_pass`
* :func:`~camille.process.mooring_fatigue`
"""

from .atm_stb import process as atm_stb
from .delta_temp import process as delta_temp
from .fft import process as fft
from .lidar import process as lidar
from .low_pass import process as low_pass
from .mooring_fatigue import process as mooring_fatigue

__all__ = [
    'atm_stb',
    'delta_temp',
    'fft',
    'lidar',
    'low_pass',
    'mooring_fatigue',
]
