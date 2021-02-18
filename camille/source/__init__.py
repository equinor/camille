"""\
Sources
==========
This module is a collection of functions reading inputs.

Notes
-----
Used data formats might be too specific, so currently module is mainly
intended for internal use

Available functions
-------------------
* :func:`~camille.source.bazefetcher`
* :func:`~camille.source.windiris`
"""


from .bazefetcher import Bazefetcher, TagNotFoundError
from .windiris import windiris
from .zephyre import Zephyre


__all__ = [
    'Bazefetcher',
    'windiris',
    'Zephyre',
]
