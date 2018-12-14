"""\
Utils
==========
This module is a collection of utility functions.

Available functions
-------------------
* :func:`~camille.util.baze_iterator`
* :func:`~camille.util.resample`
* :func:`~camille.util.sn_curve`
"""

from .baze_iterator import baze_iterator
from .resample import resample
from .sncurves import sn_curve

__all__ = [
    'baze_iterator',
    'resample',
    'sn_curve',
]
