.. image:: https://img.shields.io/badge/Python-2.7,%203.6-green.svg
    :target: https://pypi.org/project/grafana-wtf/

.. image:: https://img.shields.io/pypi/v/grafana-wtf.svg
    :target: https://pypi.org/project/grafana-wtf/

.. image:: https://img.shields.io/github/tag/daq-tools/grafana-wtf.svg
    :target: https://github.com/daq-tools/grafana-wtf

|

###########
grafana-wtf
###########


*****
About
*****
grafana-wtf - grep through all Grafana entities in the spirit of `git-wtf`_.

.. _git-wtf: http://thrawn01.org/posts/2014/03/03/git-wtf/


********
Synopsis
********
Search Grafana API for string "weatherbase".
::

    grafana-wtf find weatherbase

Display 50 most recent changes across all dashboards.
::

    grafana-wtf log --number=50


***********
Screenshots
***********

``grafana-wtf find``
====================
.. image:: https://user-images.githubusercontent.com/453543/51694547-5c78fd80-2001-11e9-96ea-3fcc2e0fb016.png

``grafana-wtf log``
===================
.. image:: https://user-images.githubusercontent.com/453543/56455736-87ee5880-6362-11e9-8cd2-c356393d09c4.png


*****
Setup
*****

Install ``grafana-wtf``
=======================
::

    pip install grafana-wtf


Configure Grafana
=================
Please take these steps to create an API key with your Grafana instance:

- Go to ``https://daq.example.org/grafana/org/apikeys``.

- Choose "New API Key".

  - Key name: grafana-wtf
  - Role: Admin

- From the output ``curl -H "Authorization: Bearer eyJrIjoiWHg...dGJpZCI6MX0=" ...``,
  please take note of the Bearer token. This is your Grafana API key.


*******
Running
*******

Before running ``grafana-wtf``, define URL and access token of your Grafana instance::

    export GRAFANA_URL=https://daq.example.org/grafana/
    export GRAFANA_TOKEN=eyJrIjoiWHg...dGJpZCI6MX0=

Then::

    grafana-wtf find weatherbase

.. note::

    ``grafana-wtf`` will cache HTTP responses for 300 seconds by default.
    When running it with the ``--drop-cache`` option, it will drop its cache upfront.


********
Examples
********
See `grafana-wtf examples <https://github.com/daq-tools/grafana-wtf/blob/master/doc/examples.rst>`_.
