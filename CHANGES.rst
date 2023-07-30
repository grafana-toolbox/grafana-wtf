#####################
grafana-wtf changelog
#####################


in progress
===========

2023-07-30 0.15.2
=================
- Improve finding unused datasources. Thanks, @meyerder.

2023-07-21 0.15.1
=================
- Fix processing panels without title. Thanks, @nikodemas and @atavakoliyext.

2023-03-06 0.15.0
=================
- Explore dashboards: Ignore ``-- Mixed --`` data sources
- Caching: Increase default cache TTL to five minutes again
- Caching: Optionally configure TTL using environment variable ``CACHE_TTL``
- History: Stop ``grafana-wtf log <UID>`` acquiring *all* dashboards
- Refactoring: Move all report renderers to ``grafana_wtf.report``
- History: Add ``id`` and ``uid`` dashboard attributes to report
- History: Unlock YAML export format
- History: Add new options ``--head``, ``--tail``, and ``--reverse``
- Search: Unlock JSON and YAML export formats
- History: Add SQL querying capabilities

2023-03-05 0.14.1
=================
- Fix ``collect_datasource_items`` when hitting special templated datasource.
  Thanks, @mauhiz.

2023-02-09 0.14.0
=================
- Add ``--dry-run`` option for ``replace`` subcommand. Thanks, @TaylorMutch.
- Update dependencies to their most recent versions.
- Add URLs to dashboard variables and panel view/edit pages to the output of
  the ``find`` subcommand. Thanks, @oplehto.
- Improve display of progressbar wrt. being interrupted by logging output.
- Improve caching

  - Use cache database location within user folder
  - Send cache database location to log
  - Reduce default cache TTL from five minutes to 60 seconds
- Drop support for Python 3.6
- Improve discovery of data sources defined by dashboard variables

2022-06-19 0.13.4
=================
- CI: Use most recent Grafana 7.5.16, 8.5.6, and 9.0.0
- Fix dashboard exploration when the ``annotations.list`` slot is ``None``
  instead of an empty list. Thanks, @TaylorMutch!

2022-03-25 0.13.3
=================
- Add option to ignore untrusted SSL certificates. Thanks, @billabongrob!

2022-03-25 0.13.2
=================
- Use ``grafana-client-2.1.0``, remove monkeypatch
- Tests: Improve fixture ``create_datasource`` to clean up afterwards
- Tests: Add fixture ``create_dashboard`` to create dashboards at runtime
- Tests: Disable caching in test mode
- Tests: Make test suite clean up its provisioned assets from Grafana
- Tests: Run Grafana on non-standard port 33333
- Tests: Add flag ``CLEANUP_RESOURCES`` to determine whether to clean up
  all resources provisioned to Grafana.
- Tests: Improve test quality, specifically for ``explore dashboards`` on
  Grafana 6 vs. Grafana >= 7
- Tests: Make test case for ``explore datasources`` use _two_ data sources
- Tests: Mimic Grafana 7/8 on datasource references within dashboards, newer
  versions have objects (uid, type) instead of bare names
- Fix implementation flaw reported at #32. Thanks, @IgorOhrimenko and @carpenterbees!
- CI: Use most recent Grafana 7.5.15 and 8.4.4

2022-02-03 0.13.1
=================
- Switch to the ``grafana-client`` library fork

2022-01-22 0.13.0
=================
- CI: Use most recent Grafana 8.3.3
- Add two more examples about using ``explore dashboards`` with ``jq``
- CI: Prepare test suite for testing two different dashboard schema versions, v27 and v33
- Improve determinism by returning stable sort order of dashboard results
- Improve compatibility with Grafana 8.3 by handling dashboard schema version 33 properly
- Reestablish compatibility with Grafana 6
- Confirm compatibility with Grafana 8.3.4

2021-12-11 0.12.0
=================
- Rename subcommand ``datasource-breakdown`` to ``explore datasources``
- Add subcommand ``explore dashboards``, e.g. for discovering dashboards using
  missing data sources.
- CI/GHA test matrix: Use Grafana 7.5.12 and 8.3.2
- Add subcommand ``info``, to display Grafana version and statistics about all entities
- For ``info`` subcommand, add Grafana ``url`` attribute
- Add example how to print the Grafana version using the ``info`` subcommand
- Add more information about dashboard entities to ``info`` subcommand
- Blackify code base
- Add ``Dockerfile`` and GHA recipe to publish container images to GHCR

2021-12-10 0.11.1
=================
- Be more graceful when decoding Grafana dashboard data structures. Thanks, @jangaraj!

2021-12-10 0.11.0
=================
- Upgrade to ``colored==1.4.3``. Thanks, @dslackw!
- Tests: Use ``.env`` file for propagating environment variables to Docker Compose
- CI/GHA test matrix: Use Grafana 7.5.11 and 8.3.1 and add Python 3.10
- Add feature to explore datasources, specifically for finding unused ones.
  Thanks, @chenlujjj!

2021-10-01 0.10.0
=================
- Improve behaviour of "replace" action by clearing the cache
- Croak when obtaining unknown report format
- Use ANSI colors only on TTYs
- Add software tests, with CI on GHA
- Add monkeypatch for grafana-api package to mitigate flaw with "replace" action.
  See also https://github.com/m0nhawk/grafana_api/pull/85.
- Bump/improve dependency versions to 3rd-party packages
- Run tests on CI against different versions of Grafana
- Add a tabular report to the find command. Thanks, @cronosnull!

2019-11-06 0.9.0
================
- Add option ``--select-dashboard`` to scan specific dashboards by list of uids
- Bump dependent modules to their most recent versions
- Add option to replace string within dashboard

2019-05-08 0.8.1
================
- Compensate for leading slash in API URL inserted by ``grafana_api``. Thanks, `@jangaraj`_.

2019-05-08 0.8.0
================
- Add "--http-logging" option

2019-05-08 0.7.0
================
- Improve search performance
- Improve report output. Add title, folder, uid, created, updated fields for dashboards.
- Fix progressbar shutdown

2019-05-08 0.6.1
================
- Improve progressbar behavior
- Upgrade required packages to their recent versions

2019-05-08 0.6.0
================
- Add "--concurrency" option to run multiple requests in
  parallel as requested through #2. Thanks, `@jangaraj`_.
- Extend non_leaf_nodes with "list" and "links"
- Improve logging

2019-05-07 0.5.0
================
- Raise the limit for ``search_dashboards()`` to its maximum value (5000).
  Thanks, `@jangaraj`_.

2019-05-07 0.4.0
================
Slightly improve the situation with large Grafana installations, see #2.
Thanks, `@jangaraj`_.

- Add option ``--cache-ttl`` for controlling the cache expiration time
- Improve error logging when hitting Grafana unauthorized
- Improve performance of search routine

.. _@jangaraj: https://github.com/jangaraj

2019-04-21 0.3.1
================
- Add progress indicator
- Improve logging and reporting


2019-04-20 0.3.0
================
- Add ``grafana-wtf log`` subcommand for displaying edit history


2019-04-10 0.2.0
================
- Add missing dependency "jsonpath-rw"


2019-01-24 0.1.0
================
- Add proof-of-concept implementation
- Add Grafana API key token authentication
- Add HTTP response caching and "--drop-cache" option
