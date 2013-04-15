#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os.path import dirname, join as join_path
from setuptools import setup, find_packages

def _read(file_name):
    sock = open(file_name)
    text = sock.read()
    sock.close()
    return text
    


setup(
    name = 'alkey',
    version = '0.2.3',
    description = 'Redis backed tool for generating cache keys.',
    long_description = _read('README.md'),
    author = 'James Arthur',
    author_email = 'username: thruflo, domain: gmail.com',
    url = 'http://github.com/thruflo/alkey',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: Public Domain',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Framework :: Pylons',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    license = _read('UNLICENSE').split('\n')[0],
    packages = find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data = True,
    zip_safe = False,
    install_requires=[
        'zope.component',
        'zope.interface',
        'sqlalchemy',
        'redis'
    ]
)
