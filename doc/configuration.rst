.. _configuration:

Configuration
=============

Main application configuration is done using plain ``.ini`` files. An example
file can be find in the source repository.

The config file is searched for in different paths. Resolution is handled via
`config_resolver <https://config-resolver.readthedocs.io/>`_ See its
documentation for details.

The current configuration template file contains the following:

.. literalinclude:: ../app.ini.dist
    :language: ini
