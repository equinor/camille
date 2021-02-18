"""\
Outputs
==========
This module is a collection of functions producing outputs.

Notes
-----
Used data formats might be too specific, so currently module is mainly
intended for internal use

Available functions
--------------------
* :func:`~camille.output.bazefetcher`
"""

from .bazefetcher import Bazefetcher

__all__ = [
    'bazefetcher'
]
