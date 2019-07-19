#!/usr/bin/env python

import pybind11
from setuptools import setup, Extension

ext_modules = [
    Extension(
        'camille.process.lidar2extension',
        ['camille/process/lidar2.cpp'],
        include_dirs=[
            # Path to pybind11 headers
            pybind11.get_include(),
            pybind11.get_include(user=True)
        ],
        language='c++'
    ),
]

setup(
    name='camille',
    packages=[
        'camille',
        'camille/output',
        'camille/process',
        'camille/source',
        'camille/util',
    ],
    ext_modules=ext_modules,
    author='Software Innovation Bergen, Equinor ASA',
    author_email='fg_gpl@equinor.com',
    description='Camille Wind',
    url='http://github.com/Statoil/camille',
    install_requires=['numpy', 'pandas', 'scipy', 'rainflow'],
    test_suite='tests',
    setup_requires=['pytest-runner', 'setuptools >=28', 'setuptools_scm'],
    tests_require=['pytest', 'pytest-repeat'],
    use_scm_version=True,
)
