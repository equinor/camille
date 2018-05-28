#!/usr/bin/env python

from setuptools import setup

_requirements = []
with open('requirements.txt', 'r') as f:
    _requirements = [line.strip() for line in f]

setup(
    name='camille',
    packages=[
        'camille',
        'camille/processors',
    ],
    author='Software Innovation Bergen, Equinor ASA',
    author_email='fg_gpl@equinor.com',
    description="Camille Wind",
    install_requires=_requirements,
    test_suite='tests',
)
