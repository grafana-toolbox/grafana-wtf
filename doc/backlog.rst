###################
grafana-wtf backlog
###################


******
Prio 1
******
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
