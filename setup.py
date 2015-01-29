#!/usr/bin/env python2.7

from setuptools import setup

long_description = """\
vSphere Client for Python is pure-Python implementation of
collection tools to access to VMware's vSphere API.
It provides both a Python API and a CLI to manage vSphere.
"""

pkgdir = {'': 'src'}

setup(
    name = 'vsphere',
    version = '1.0.0',
    description = 'vsphere-cli: VMware vSphere API and CLI management tool',
    keywords = 'vmware api vsphere cli admin tool',
    long_description = long_description,
    author = 'Alcatel-Lucent Enterprise Personal Cloud R&D',
    author_email = 'dev@opentouch.net',
    url = 'https://github.com/OpenTouch/vsphere-client',
    package_dir=pkgdir,
    packages=['vsphere'],
    include_package_data=True,
    scripts=['bin/vsphere'],
    platforms = ['All'],
    license = 'Apache 2.0',
)
