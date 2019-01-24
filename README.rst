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
Search Grafana API for string "ldi_readings".
::

    grafana-wtf find ldi_readings

.. note::

    ``grafana-wtf`` will cache HTTP responses for 300 seconds,
    unless running with the ``--drop-cache`` option.


*****
Setup
*****

Install
-------
::

    pip install grafana-wtf


Configure
---------
Create an API key by:

- Go to https://daq.example.org/grafana/org/apikeys
- Choose "New API Key"
  - Key name: grafana-wtf
  - Role: Admin
- From the output ``curl -H "Authorization: Bearer eyJrIjoiWHg...dGJpZCI6MX0=" ...``,
  please take note of the Bearer token. This is your Grafana API key.


********
Examples
********
See `grafana-wtf examples <https://github.com/daq-tools/grafana-wtf/blob/master/doc/examples.rst>`_.
