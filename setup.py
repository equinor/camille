#!/usr/bin/env python

from setuptools import setup

setup(
    name='camille',
    packages=[
        'camille',
        'camille/processors',
        'camille/utils',
    ],
    author='Software Innovation Bergen, Equinor ASA',
    author_email='fg_gpl@equinor.com',
    description='Camille Wind',
    url='http://github.com/Statoil/camille',
    install_requires=['numpy', 'pandas', 'scipy', 'rainflow'],
    test_suite='tests',
    setup_requires=['pytest-runner', 'setuptools >=28', 'setuptools_scm'],
    tests_require=['pytest'],
    use_scm_version={'write_to': 'camille/version.py'},
)
