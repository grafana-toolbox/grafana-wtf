#####################
grafana-wtf changelog
#####################


in progress
===========
- Upgrade to ``colored==1.4.3``

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
