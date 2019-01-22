DEWI realtime sync: Sync a directory structure
==============================================

Name
----
DEWI: Old Welsh form of David

The name is chosen because of the similarity to DWA, which was the project's
original name, which stands for Developer's Work Area.


Purpose
-------

A project under development may need to be tested somewhere else, either from another directory
or from another host (server). This can be done by current package: any file system change is
synchronized immediately either to a local directory or over SSH to a remote directory.


Installation
------------

It can be installed from source::

        python3 setup.py

Or from pip::

        pip install dewi_realtime_sync
