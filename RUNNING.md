# Running the `fix/nested-collapsed-row-queries` branch locally

Steps to clone the fork, switch to the fix branch, install, and run the tool.

```bash
# 1. Clone the fork and enter it
git clone git@github.com:PrayagS/grafana-wtf.git
cd grafana-wtf

# 2. Switch to the fix branch
git checkout fix/nested-collapsed-row-queries

# 3. Create + activate a virtualenv (Python 3.8+)
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 4. Install the tool in editable mode (add [test] for the test deps)
pip install --editable '.[test]'

# 5. Point at the Grafana instance
export GRAFANA_URL=https://your-grafana.example.org/
export GRAFANA_TOKEN=your_api_token

# 6. Run it — the command from the README
grafana-wtf --concurrency=12 explore dashboards --data-details --queries-only --format=json \
  | jq '.[].details | values[] | .[] | .expr,.jql,.query,.rawSql | select( . != null and . != "" )'

# 7. (optional) run the tests
pytest tests/test_model.py
```

## Useful recipes

Every recipe filters dashboard queries by a **datasource + string** combination:

- `--arg ds` — datasource filter (regex), matched against the panel datasource `type` **or** `uid`. E.g. `prometheus`, `influxdb`, or a specific datasource uid.
- `--arg needle` — string/regex to search for inside the query (`expr`/`rawSql`/`query`/`jql`).

> All recipes require this branch's fix — many matching panels live inside
> collapsed rows, which upstream drops.
>
> Add `--select-dashboard=<uid1>,<uid2>` before `explore` to limit the scan
> (faster, and avoids aborting on one broken dashboard):
>
> ```bash
> grafana-wtf --select-dashboard=x9UNSpiNk explore dashboards --data-details --queries-only --format=json | jq ...
> ```

### 1. Panel links for matching queries

Print the direct panel link plus the matching query, one per line. Panel
link format is `<dashboard-url>?viewPanel=<id>`.

```bash
grafana-wtf explore dashboards --data-details --queries-only --format=json \
| jq -r --arg ds "prometheus" --arg needle "istio_" '
    .[] | .dashboard.url as $url
    | .details.panels[]
    | select((.datasource | if type=="object" then (.type//"")+" "+(.uid//"") else tostring end) | test($ds))
    | select([.expr,.rawSql,.query,.jql] | map(select(.!=null)) | join(" ") | test($needle))
    | "\($url)?viewPanel=\(._panel.id)\t\((.expr//.rawSql//.query//.jql) | gsub("\\s+";" "))"
'
```

Output is tab-separated: `<panel link>\t<matching query>`.

Example output (Prometheus + `istio_`):

```
https://grafana.example.org/d/x9UNSpiNk/fraud-prevention-service?viewPanel=253	100 * (( sum by (destination_service)( rate(istio_requests_total...
https://grafana.example.org/d/x9UNSpiNk/fraud-prevention-service?viewPanel=255	round( sum by (source_canonical_service)( irate( istio_requests_total...
```

### 2. Pretty list: dashboard title, panel title, panel link, query

Human-readable listing of each matching query with its context.

```bash
grafana-wtf explore dashboards --data-details --queries-only --format=json \
| jq -r --arg ds "prometheus" --arg needle "istio_" '
    .[] | .dashboard as $d
    | .details.panels[]
    | select((.datasource | if type=="object" then (.type//"")+" "+(.uid//"") else tostring end) | test($ds))
    | select([.expr,.rawSql,.query,.jql] | map(select(.!=null)) | join(" ") | test($needle))
    | "\u2022 \($d.title) \u203a \(._panel.title // "untitled")\n  link:  \($d.url)?viewPanel=\(._panel.id)\n  query: \((.expr//.rawSql//.query//.jql) | gsub("\\s+";" "))\n"
'
```

Example output:

```
• Fraud Prevention Service › Outgoing requests (Service Level) DOD%
  link:  https://grafana.example.org/d/x9UNSpiNk/fraud-prevention-service?viewPanel=253
  query: sum by (destination_service)( rate(istio_requests_total{ source_canonical_service="fraud-prevention", reporter="source" }[15m]) )

• Fraud Prevention Service › Incoming Traffic (Service Level) WOW %
  link:  https://grafana.example.org/d/x9UNSpiNk/fraud-prevention-service?viewPanel=255
  query: round( sum by (source_canonical_service)( irate( istio_requests_total{ destination_canonical_service="fraud-prevention", reporter="destination" }[15m] ) ), 0.001 )
```

### 3. Just the matching queries

Bare query strings only (no links/titles).

```bash
grafana-wtf explore dashboards --data-details --queries-only --format=json \
| jq -r --arg ds "prometheus" --arg needle "istio_" '
    .[] | .details.panels[]
    | select((.datasource | if type=="object" then (.type//"")+" "+(.uid//"") else tostring end) | test($ds))
    | (.expr//.rawSql//.query//.jql) | select(.!=null) | select(test($needle))
'
```

## Notes

- **Using `uv` instead** of venv+pip: `uv sync` then `uv run grafana-wtf ...`.
- `jq` and a valid token with dashboard read access are prerequisites.
- The fix is code-only, so no extra build step — the editable install picks it up.
