###################
grafana-wtf backlog
###################


******
Prio 1
******
- [o] Introduce paging to reach beyond the 5000 results limit,
  see https://grafana.com/docs/http_api/folder_dashboard_search/
- [o] Introduce concurrent resource fetching using asyncio or grequests,
  see https://github.com/kennethreitz/grequests
- [o] Case insensitive and regex searching
- [o] Show dependencies

******
Prio 2
******
- [o] Mode for restricting search to queries only
- [o] Scan folders
- [o] grafana-wtf dump
- [o] grafana-wtf log --tail | discourse
- [o] grafana-wtf log --tail | wtee
- [o] grafana-wtf export/import


****
Done
****
- [x] Add HTTP response caching and "--drop-cache" option
- [x] Add progress indicator (tqdm)
