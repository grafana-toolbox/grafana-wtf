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

Query-extraction recipes (grep by datasource + string, panel links, pretty
listing) live in [RECIPES.md](RECIPES.md).

## Notes

- **Using `uv` instead** of venv+pip: `uv sync` then `uv run grafana-wtf ...`.
- `jq` and a valid token with dashboard read access are prerequisites.
- The fix is code-only, so no extra build step — the editable install picks it up.
