###################
grafana-wtf backlog
###################


******
Prio 1
******
- [o] Dockerize
- [o] Statistics reports for data sources and panels: https://github.com/panodata/grafana-wtf/issues/18
- [o] Finding invalid data sources: https://github.com/panodata/grafana-wtf/issues/19


********
Prio 1.5
********
- [o] Check if we can collect metrics from Grafana
      - https://grafana.com/docs/grafana/latest/administration/view-server/internal-metrics/
      - https://grafana.com/docs/grafana/latest/developers/plugins/backend/#collect-metrics
- [o] Add test fixture which completely resets everything in Grafana before running the test harness.
      Move to a different port than 3000 then!
- [o] Improve output format handling and error cases
- [o] Introduce paging to reach beyond the 5000 results limit,
  see https://grafana.com/docs/http_api/folder_dashboard_search/
- [o] Case insensitive and regex searching
- [o] Show dependencies
- [o] Optionally apply "replace" to data sources also
- [o] Add software tests for authenticated access to Grafana (--grafana-token)


******
Prio 2
******
- [o] Mode for restricting search to queries only
- [o] Also scan folders
- [o] grafana-wtf dump
- [o] grafana-wtf log --tail | discourse
- [o] grafana-wtf log --tail | wtee
- [o] grafana-wtf export/import


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
