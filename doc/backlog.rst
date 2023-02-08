###################
grafana-wtf backlog
###################


******
Prio 1
******
- [o] Expand searching via ``find`` subcommand to other entities
- [o] Add output format JSON for ``find`` subcommand
- [o] Add subcommand for checking data source health
- [o] Provide environment variable for ``--drop-cache``
- [o] Does it croak on play.grafana.org?
- [o] Don't display "Global" section when it's mostly empty.


*********
Prio 1.10
*********
- [o] With Grafana >8.3, resolve datasource name and add to ``{'type': 'influxdb', 'uid': 'PDF2762CDFF14A314'}``
- [o] Add "folder name/uid" to "explore dashboards" response.
- [o] Check if "datasources" is always present in responses to "explore dashboards".


*********
Prio 1.25
*********
- [o] Statistics reports for data sources and panels: https://github.com/panodata/grafana-wtf/issues/18
- [o] Finding invalid data sources: https://github.com/panodata/grafana-wtf/issues/19
- [o] Add subcommand ``dump`` for dumping whole documents from the API, unmodified


********
Prio 1.5
********
- [o] Search through more Grafana entities (users, organizations, teams)
- [o] Improve output format handling and error cases
- [o] Introduce paging to reach beyond the 5000 results limit,
  see https://grafana.com/docs/http_api/folder_dashboard_search/
- [o] Case insensitive and regex searching
- [o] Show dependencies
- [o] Optionally apply "replace" to data sources also
- [o] Add software tests for authenticated access to Grafana (--grafana-token)
- [o] Add output format RSS


******
Prio 2
******
- [o] Mode for restricting search to queries only
- [o] Also scan folders
- [o] grafana-wtf dump
- [o] grafana-wtf log --tail | discourse
- [o] grafana-wtf log --tail | wtee
- [o] grafana-wtf export/import
- [o] Check if we can collect metrics from Grafana
      - https://grafana.com/docs/grafana/latest/administration/view-server/internal-metrics/
      - https://grafana.com/docs/grafana/latest/developers/plugins/backend/#collect-metrics


****
Done
****
- [x] Add HTTP response caching and "--drop-cache" option
- [x] Add progress indicator (tqdm)
- [x] Introduce concurrent resource fetching using asyncio or grequests,
  see https://github.com/kennethreitz/grequests
- [x] Add software tests
- [x] Document "replace" feature in README
- [x] AttributeError: https://github.com/panodata/grafana-wtf/issues/17
- [/] Repair ``log`` subcommand
- [x] Add subcommand ``explore dashboards``
- [x] Add subcommand ``info``
    - Display Grafana version: https://grafana.com/docs/grafana/latest/http_api/other/#health-api
    - Display number of dashboards, folders, users, and playlists
- [x] Blackify
- [x] Dockerize
- [x] Add test fixture for adding dashboards at runtime from branch ``amo/test-dashboard-runtime``
- [x] Improve test suite wrt. test case isolation vs. Grafana resources
- [x] Add test fixture which completely resets everything in Grafana before running the test harness.
- [x] Move test harness Grafana to a different port than 3000
