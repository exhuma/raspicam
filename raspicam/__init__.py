'''
This module contains shortcuts to simplify accessing package internals when
using raspicam as a form of library, or scripting it.
'''

from os.path import dirname, join

from .main import Application

with open(join(dirname(__file__), 'version.txt')) as fp:
    __version__ = fp.read().strip()
