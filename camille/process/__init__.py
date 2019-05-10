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
* :func:`~camille.process.high_pass`
* :func:`~camille.process.band_pass`
* :func:`~camille.process.fatigue`
* :func:`~camille.process.rolling_median`
* :func:`~camille.process.mooring_stress`
"""

from .atm_stb import process as atm_stb
from .delta_temp import process as delta_temp
from .fft import process as fft
from .lidar import process as lidar
from .pass_filter import low_pass
from .pass_filter import high_pass
from .pass_filter import band_pass
from .fatigue import process as fatigue
from .rolling_median import process as rolling_median
from .mooring_stress import process as mooring_stress

__all__ = [
    'atm_stb',
    'delta_temp',
    'fft',
    'lidar',
    'low_pass',
    'high_pass',
    'band_pass',
    'fatigue',
    'rolling_median',
    'mooring_stress'
]
