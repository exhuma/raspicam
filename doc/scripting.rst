Scripted Usage
==============

A simple way to run the application form a scripted environment::

    >>> from raspicam import Application
    >>> app = Application()
    >>> app.init()
    >>> app.run()

The ``init`` method is implemented separately from the ``__init__`` initialiser
to provide a no-args "constructor" which does not perform any magic. This
*should* make testing easier.

Note that configuration is handled via a config-file which controls
site-specific configuration and is searched for by :py:mod:`config_resolver`.
Have a look at ``app.ini.dist`` as well, which lives in the source repository
for a template of the config file.


Customized Pipeline
-------------------

See also :ref:`architecture`

By following the script above, you will get the exact same behaviour as running
the application from the ``main`` module. It is likely that you would like to
control the steps taken to modify images. This can be achieved by providing an
alternative "pipeline". The easiest way to achieve this is to subclass
:py:class:`~raspicam.pipeline.DefaultPipeline` and supply an alternative set of
operations (see :py:mod:`raspicam.operations` for available operations)::


    from raspicam.main import Application
    from raspicam.pipeline import DetectionPipeline, resizer, togray, blur
    from raspicam.localtypes import Dimension


    class MyPipeline(DetectionPipeline):

        def __init__(self):
            super().__init__([
                resizer(Dimension(320, 240)),
                togray,
                blur(11),
            ])


    app = Application()
    # Using "None" as cli_args will default to "sys.argv[1:]"
    app.init(None, custom_pipeline=MyPipeline())
    app.run()
