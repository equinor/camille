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
from .utcdate import utcdate

__all__ = [
    'resample',
    'utcdate',
]
