'''
This module contains shortcuts to simplify accessing package internals when
using raspicam as a form of library, or scripting it.

The raspicam package started as a sandbox to play with the RasperryPi camera
module, but has evolved to a simple tool to run motion detection. And
potentially other use-cases through the implementation of image "pipelines".
Theses pipelines currently exchange data which was aimed at motion detection
though, so it may or may not be applicable to other use-cases!

A simple way to run the application form a scripted environment::

    >>> from raspicam import Application
    >>> app = Application()
    >>> app.init()
    >>> app.run()

The ``init`` method is implemented separately from the ``__init__`` initialiser
to provide a no-args "constructor" which does not perform any magic. This
*should* make testing easier. See the documentation for the different methods to
see how you can change the default behaviour.

Note that configuration is handled via a config-file which controls
site-specific configuration and is searched for by ``config_resolver``. Have a
look at ``app.ini.dist`` as well, which lives in the source repository for a
template of the config file.
'''

from .main import Application
