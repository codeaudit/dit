#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Installation script for dit.

"""

from __future__ import print_function

import ast
import os
import re
import sys
import warnings

try:
    from setuptools import setup
    has_setuptools = True
except ImportError:
    from distutils.core import setup
    has_setuptools = False

import distutils
from distutils.core import Extension
from distutils.command import install_data
from distutils.command.build_ext import build_ext

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('dit/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

class my_install_data(install_data.install_data):
    # A custom install_data command, which will install it's files
    # into the standard directories (normally lib/site-packages).
    def finalize_options(self):
        if self.install_dir is None:
            installobj = self.distribution.get_command_obj('install')
            self.install_dir = installobj.install_lib
        print('Installing data files to {0}'.format(self.install_dir))
        install_data.install_data.finalize_options(self)

def has_cython():
    """Returns True if Cython is found on the system."""
    try:
        import Cython
        return True
    except ImportError:
        return False

def check_opt(name):
    x = eval('has_{0}()'.format(name.lower()))
    msg = "%(name)s not found. %(name)s extensions will not be built."
    if not x:
        warnings.warn(msg % {'name':name})
    return x

def hack_distutils(debug=False, fast_link=True):
    # hack distutils.sysconfig to eliminate debug flags
    # stolen from mpi4py

    def remove_prefixes(optlist, bad_prefixes):
        for bad_prefix in bad_prefixes:
            for i, flag in enumerate(optlist):
                if flag.startswith(bad_prefix):
                    optlist.pop(i)
                    break
        return optlist

    import sys
    if not sys.platform.lower().startswith("win"):
        from distutils import sysconfig

        cvars = sysconfig.get_config_vars()
        cflags = cvars.get('OPT')
        if cflags:
            cflags = remove_prefixes(cflags.split(),
                    ['-g', '-O', '-Wstrict-prototypes', '-DNDEBUG'])
            if debug:
                cflags.append("-g")
            else:
                cflags.append("-O3")
                cflags.append("-DNDEBUG")
            cvars['OPT'] = str.join(' ', cflags)
            cvars["CFLAGS"] = cvars["BASECFLAGS"] + " " + cvars["OPT"]

        if fast_link:
            for varname in ["LDSHARED", "BLDSHARED"]:
                ldsharedflags = cvars.get(varname)
                if ldsharedflags:
                    ldsharedflags = remove_prefixes(ldsharedflags.split(),
                            ['-Wl,-O'])
                    cvars[varname] = str.join(' ', ldsharedflags)

def main():
    ## Probably, we don't need this anymore?
    hack_distutils()

    # Handle optional extensions.
    opt = {}
    for name, option in [('Cython', 'nocython')]:
        lname = name.lower()

        # Determine if the Python module exists
        opt[lname] = check_opt(name)

        if not opt[lname]:
            continue
        else:
            # Disable installation of extensions, if user requested.
            try:
                idx = sys.argv.index("--{0}".format(option))
            except ValueError:
                pass
            else:
                opt[lname] = False
                del sys.argv[idx]

    cmdclass = {'install_data': my_install_data}

    cython_modules = []
    if opt['cython']:
        import Cython.Distutils
        try:
            import numpy as np
        except ImportError:
            msg = "Please install NumPy first."
            print(msg)
            raise

        cmdclass['build_ext'] = Cython.Distutils.build_ext

        cython_modules = []

        close = Extension(
            "dit.math._close",
            ["dit/math/_close.pyx"]
        )

        pycounts = Extension(
            "dit.inference.pycounts",
            ["dit/inference/pycounts.pyx", "dit/inference/counts.c"],
            include_dirs=[np.get_include()],
            libraries=['m'],
            extra_compile_args=['-std=c99'],
        )

        samplediscrete = Extension(
            "dit.math._samplediscrete",
            ["dit/math/_samplediscrete.pyx"],
            include_dirs=[np.get_include()]
        )

        # Active Cython modules
        cython_modules = [
            close,
            pycounts,
            samplediscrete,
        ]

    other_modules = []

    ext_modules = cython_modules + \
                  other_modules

    data_files = ()

    with open('requirements.txt') as reqs:
        install_requires = reqs.read().splitlines()

    if sys.version_info[:2] <= (3, 3):
        with open('requirements_lt33.txt') as reqs:
            install_requires.extend(reqs.read().splitlines())

    packages = [
        'dit',
        'dit.algorithms',
        'dit.divergences',
        'dit.example_dists',
        'dit.inference',
        'dit.math',
        'dit.multivariate',
        'dit.other',
        'dit.profiles',
        'dit.shannon',
        'dit.utils',
    ]

    # Tests
    # This includes for bdist only. sdist uses MANIFEST.in
    package_data = dict(zip(packages, [['tests/*.py']]*len(packages)))

    kwds = {
        'name':                 "dit",
        'version':              version,
        'url':                  "http://dit.io",

        'packages':             packages,
        'package_data':         package_data,
        'provides':             ['dit'],
        'install_requires':     install_requires,
        'ext_modules':          ext_modules,
        'cmdclass':             cmdclass,
        'data_files':           data_files,
        'include_package_data': True,

        'author':               "Humans",
        'author_email':         "admin@dit.io",
        'description':          "Python package for information theory.",
        'long_description':     open('README.rst').read(),
        'license':              "BSD",
    }

    # Automatic dependency resolution is supported only by setuptools.
    if not has_setuptools:
        del kwds['install_requires']

    setup(**kwds)

if __name__ == '__main__':
    if sys.argv[-1] == 'setup.py':
        print("To install, run 'python setup.py install'\n")

    v = sys.version_info[:2]
    if v < (2, 7):
        msg = "dit requires Python version >= 2.7"
        print(msg.format(v))
        sys.exit(-1)

    main()
