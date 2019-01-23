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

from .resample import resample
from .sncurves import sn_curve

__all__ = [
    'BazeIter',
    'resample',
    'sn_curve',
]
