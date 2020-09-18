#!/usr/bin/env python

import skbuild
import setuptools


class get_pybind_include(object):
    def __init__(self, user=False):
        self.user = user

    def __str__(self):
        # postpone importing pybind11 until building actually happens
        import pybind11
        return pybind11.get_include(self.user)


pybind_includes = [
    str(get_pybind_include()),
    str(get_pybind_include(user = True))
]


skbuild.setup(
    name='camille',
    packages=[
        'camille',
        'camille/output',
        'camille/process',
        'camille/source',
        'camille/util',
    ],
    author='Software Innovation Bergen, Equinor ASA',
    author_email='fg_gpl@equinor.com',
    description='Camille Wind',
    url='http://github.com/Statoil/camille',
    install_requires=['numpy', 'pandas', 'scipy', 'rainflow', 'requests'],
    test_suite='tests',
    setup_requires=[
        'pytest-runner',
        'setuptools >=28',
        'setuptools_scm',
        'cmake',
        'pybind11',
    ],
    tests_require=['pytest', 'pytest-repeat'],
    # we're building with the pybind11 fetched from pip. Since we don't rely on
    # a cmake-installed pybind there's also no find_package(pybind11) -
    # instead, the get include dirs from the package and give directly from
    # here
    cmake_args = [
        '-DPYBIND11_INCLUDE_DIRS=' + ';'.join(pybind_includes),
        # we can safely pass OSX_DEPLOYMENT_TARGET as it's ignored on
        # everything not OS X. We depend on C++11, which makes our minimum
        # supported OS X release 10.9
        '-DCMAKE_OSX_DEPLOYMENT_TARGET=10.9',
    ],

    use_scm_version=True,
    cmdclass = { 'test': setuptools.command.test.test },
)
