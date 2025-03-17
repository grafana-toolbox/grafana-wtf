###########
grafana-wtf
###########

|

.. start-badges

|ci-tests| |ci-coverage| |license| |pypi-downloads|
|python-versions| |status| |pypi-version| |grafana-versions|

.. |ci-tests| image:: https://github.com/grafana-toolbox/grafana-wtf/actions/workflows/tests.yml/badge.svg
    :target: https://github.com/grafana-toolbox/grafana-wtf/actions/workflows/tests.yml

.. |ci-coverage| image:: https://codecov.io/gh/grafana-toolbox/grafana-wtf/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/grafana-toolbox/grafana-wtf
    :alt: Test suite code coverage

.. |python-versions| image:: https://img.shields.io/pypi/pyversions/grafana-wtf.svg
    :target: https://pypi.org/project/grafana-wtf/

.. |status| image:: https://img.shields.io/pypi/status/grafana-wtf.svg
    :target: https://pypi.org/project/grafana-wtf/

.. |pypi-version| image:: https://img.shields.io/pypi/v/grafana-wtf.svg
    :target: https://pypi.org/project/grafana-wtf/

.. |pypi-downloads| image:: https://static.pepy.tech/badge/grafana-wtf/month
    :target: https://pypi.org/project/grafana-wtf/

.. |license| image:: https://img.shields.io/pypi/l/grafana-wtf.svg
    :target: https://github.com/grafana-toolbox/grafana-wtf/blob/main/LICENSE

.. |grafana-versions| image:: https://img.shields.io/badge/Grafana-6.x%20--%2011.x-blue.svg
    :target: https://github.com/grafana/grafana
    :alt: Supported Grafana versions

.. end-badges


*****
About
*****
grafana-wtf - grep through all Grafana entities in the spirit of `git-wtf`_,
see also `Introduction to GIT WTF`_.

.. attention::

    This program can put significant load on your Grafana instance
    and the underlying database machinery. Handle with care!


********
Synopsis
********

Search Grafana (dashboards and datasources) for string "weatherbase".
::

    grafana-wtf find weatherbase

Display 50 most recent changes across all dashboards.
::

    grafana-wtf log --number=50

Explore dashboards and datasources in more detail.
::

    grafana-wtf explore dashboards
    grafana-wtf explore datasources

Explore plugins.
::

    grafana-wtf plugins list
    grafana-wtf plugins status

Run with Docker::

    # Access Grafana instance on localhost, without authentication.
    docker run --rm -it \
        --env GRAFANA_URL="http://host.docker.internal:3000" \
        ghcr.io/grafana-toolbox/grafana-wtf grafana-wtf info

    # Access Grafana instance with authentication.
    docker run --rm -it \
        --env GRAFANA_URL="https://grafana.example.org/grafana" \
        --env GRAFANA_TOKEN="eyJrIjoiWHg...dGJpZCI6MX0=" \
        ghcr.io/grafana-toolbox/grafana-wtf grafana-wtf info


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

    pipx install grafana-wtf


Configure Grafana
=================
Please take these steps to create an API key with your Grafana instance:

- Go to ``https://daq.example.org/grafana/org/apikeys``.

- Choose "New API Key".

  - Key name: grafana-wtf
  - Role: Admin

- From the output ``curl -H "Authorization: Bearer eyJrIjoiWHg...dGJpZCI6MX0=" ...``,
  please take note of the Bearer token. This is your Grafana API key.


*************
Configuration
*************

Grafana connection
==================

To configure to which Grafana instance to connect to, and how to authenticate, use
the ``--grafana-url`` and ``--grafana-token`` command line options.

Alternatively, before running ``grafana-wtf``, you can define URL and access token
of your Grafana instance by using environment variables::

    export GRAFANA_URL=https://daq.example.org/grafana/
    export GRAFANA_TOKEN=eyJrIjoiWHg...dGJpZCI6MX0=

In order to accept untrusted SSL certificates, append the ``?verify=no`` query string
to the ``GRAFANA_URL``::

    export GRAFANA_URL=https://daq.example.org/grafana/?verify=no

Caching
=======

``grafana-wtf`` will cache HTTP responses for 60 minutes by default, in order to save
resources, by not hitting the server each server. You can configure that setting by using
the ``--cache-ttl`` option, or the ``CACHE_TTL`` environment variable.

When invoking the program with the ``--drop-cache`` option, it will drop its cache upfront.



*****
Usage
*****


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
    grafana-wtf explore dashboards --format=json | \
        jq '.[] | select(.datasources_missing) | .dashboard + {ds_missing: .datasources_missing[] | [.name]}'

How to find dashboards using specific data sources?
::

    # Display all dashboards which use a specific data source, filtered by data source name.
    grafana-wtf explore dashboards --format=json | jq '.[] | select(.datasources | .[].name=="<datasource_name>")'

    # Display all dashboards using data sources with a specific type. Here: InfluxDB.
    grafana-wtf explore dashboards --format=json | jq '.[] | select(.datasources | .[].type=="influxdb")'

How to list all queries used in all dashboards?
::

    grafana-wtf explore dashboards --data-details --queries-only --format=json | \
        jq '.[].details | values[] | .[] | .expr,.jql,.query,.rawSql | select( . != null and . != "" )'


Searching for strings
=====================

Find the string ``weatherbase`` throughout all dashboards and data sources::

    grafana-wtf find weatherbase

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

Concurrency
===========

Use the ``--concurrency`` option, for example ``--concurrency=5``, to enable
concurrent downloading per ``ThreadPoolExecutor``.


********
Examples
********

For discovering more command line parameters and their arguments, please invoke
``grafana-wtf --help`` and have a look at `grafana-wtf examples`_.



***********
Development
***********
::

    git clone https://github.com/grafana-toolbox/grafana-wtf
    cd grafana-wtf

    # Run all tests.
    make test

    # Run selected tests.
    pytest --keepalive -vvv -k test_find_textual


.. _git-wtf: https://github.com/DanielVartanov/willgit/blob/master/bin/git-wtf
.. _grafana-wtf examples: https://github.com/grafana-toolbox/grafana-wtf/blob/main/doc/examples.rst
.. _Introduction to GIT WTF: https://web.archive.org/web/20230921074244/https://thrawn01.org/posts/2014/03/03/git-wtf/
