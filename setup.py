#!/usr/bin/env python

from setuptools import setup

setup(
    name='camille',
    packages=[
        'camille',
        'camille/processors',
    ],
    author='Software Innovation Bergen, Equinor ASA',
    author_email='fg_gpl@equinor.com',
    description="Camille Wind",
    install_requires=['numpy', 'pandas', 'scipy', 'rainflow'],
    test_suite='tests',
    setup_requires=['pytest-runner'],
    tests_require=['pytest']
)
