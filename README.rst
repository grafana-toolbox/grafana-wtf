.. image:: https://github.com/panodata/grafana-wtf/workflows/Tests/badge.svg
    :target: https://github.com/panodata/grafana-wtf/actions?workflow=Tests

.. image:: https://img.shields.io/pypi/pyversions/grafana-wtf.svg
    :target: https://pypi.org/project/grafana-wtf/

.. image:: https://img.shields.io/pypi/status/grafana-wtf.svg
    :target: https://pypi.org/project/grafana-wtf/

.. image:: https://img.shields.io/pypi/v/grafana-wtf.svg
    :target: https://pypi.org/project/grafana-wtf/

.. image:: https://pepy.tech/badge/grafana-wtf/month
    :target: https://pypi.org/project/grafana-wtf/

.. image:: https://img.shields.io/pypi/l/grafana-wtf.svg
    :target: https://github.com/panodata/grafana-wtf/blob/main/LICENSE

.. image:: https://img.shields.io/badge/Grafana-6.x%20--%209.x-blue.svg
    :target: https://github.com/grafana/grafana
    :alt: Supported Grafana versions

|

###########
grafana-wtf
###########


*****
About
*****
grafana-wtf - grep through all Grafana entities in the spirit of `git-wtf`_.

.. _git-wtf: http://thrawn01.org/posts/2014/03/03/git-wtf/

.. attention::

    This program can put significant load on your Grafana instance
    and the underlying database machinery. Handle with care!


********
Synopsis
********

Search Grafana API for string "weatherbase".
::

    grafana-wtf find weatherbase

Display 50 most recent changes across all dashboards.
::

    grafana-wtf log --number=50

Run with Docker::

    # Access Grafana instance on localhost, without authentication.
    docker run --rm -it --env GRAFANA_URL="http://host.docker.internal:3000" ghcr.io/panodata/grafana-wtf grafana-wtf info

    # Access Grafana instance with authentication.
    docker run --rm -it --env GRAFANA_URL="https://daq.grafana.org/grafana" --env GRAFANA_TOKEN="eyJrIjoiWHg...dGJpZCI6MX0=" ghcr.io/panodata/grafana-wtf grafana-wtf info


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


*****
Usage
*****

Before running ``grafana-wtf``, define URL and access token of your Grafana instance::

    export GRAFANA_URL=https://daq.example.org/grafana/
    export GRAFANA_TOKEN=eyJrIjoiWHg...dGJpZCI6MX0=

In order to ignore untrusted SSL certificates, append the ``?verify=no`` query string
to the ``GRAFANA_URL``::

    export GRAFANA_URL=https://daq.example.org/grafana/?verify=no


General information
===================

::

    # Display a bunch of meta information and statistics.
    grafana-wtf info --format=yaml

    # Display Grafana version.
    grafana-wtf info --format=json | jq -r '.grafana.version'


Explore data sources
====================

How to find unused data sources?
::

    # Display all data sources and the dashboards using them, as well as unused data sources.
    grafana-wtf explore datasources --format=yaml

    # Display names of unused datasources as a flat list.
    grafana-wtf explore datasources --format=json | jq -r '.unused[].datasource.name'


Explore dashboards
==================

How to find dashboards which use non-existing data sources?
::

    # Display some details of all dashboards, including names of missing data sources.
    grafana-wtf explore dashboards --format=yaml

    # Display only dashboards which have missing data sources, along with their names.
    grafana-wtf explore dashboards --format=json | jq '.[] | select( .datasources_missing ) | .dashboard + {ds_missing: .datasources_missing[] | [.name]}'


Searching for strings
=====================

Find the string ``weatherbase`` throughout all dashboards and data sources::

    grafana-wtf find weatherbase

.. note::

    ``grafana-wtf`` will cache HTTP responses for 300 seconds by default.
    When running it with the ``--drop-cache`` option, it will drop its cache upfront.


Replacing strings
=================

Replace all occurrences of ``ldi_v2`` with ``ldi_v3`` within dashboard with
UID ``_JJ22OZZk``::

    grafana-wtf --select-dashboard=_JJ22OZZk replace ldi_v2 ldi_v3

In order to preview the changes, you should use the ``--dry-run`` option
beforehand::

    grafana-wtf --select-dashboard=_JJ22OZZk replace ldi_v2 ldi_v3 --dry-run


Display edit history
====================

Watching out for recent editing activity on any dashboards?
::

    # Display 50 most recent changes across all dashboards.
    grafana-wtf log --number=50



********
Examples
********

For discovering more command line parameters and their arguments, please invoke
``grafana-wtf --help`` and have a look at `grafana-wtf examples`_.



***********
Development
***********
::

    git clone https://github.com/panodata/grafana-wtf
    cd grafana-wtf

    # Run all tests.
    make test

    # Run selected tests.
    pytest --keepalive -vvv -k test_find_textual


.. _grafana-wtf examples: https://github.com/panodata/grafana-wtf/blob/master/doc/examples.rst
