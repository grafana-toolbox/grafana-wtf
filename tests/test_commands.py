import warnings

from packaging import version

warnings.filterwarnings("ignore", category=DeprecationWarning, module=".*docopt.*")
import json
import logging
import re
import shlex
import sys

import docopt
import pytest
import yaml

import grafana_wtf.commands
from tests.conftest import mkdashboard


def set_command(command, more_options="", cache=False):
    cache_option = ""
    if cache is False:
        cache_option = "--cache-ttl=0"
    command = f'grafana-wtf --grafana-url="http://localhost:33333" {cache_option} {more_options} {command}'
    sys.argv = shlex.split(command)


def test_failure_grafana_url_missing():

    # Run command and capture output.
    command = "grafana-wtf find foobar"
    sys.argv = shlex.split(command)
    with pytest.raises(docopt.DocoptExit) as ex:
        grafana_wtf.commands.run()

    # Verify output.
    assert ex.match(
        re.escape('No Grafana URL given. Please use "--grafana-url" option or environment variable "GRAFANA_URL".')
    )


def test_find_textual_empty(docker_grafana, capsys):

    # Run command and capture output.
    set_command("find foobar")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()

    # Verify output.
    assert 'Searching for expression "foobar" at Grafana instance http://localhost:33333' in captured.out
    assert "Data Sources: 0 hits" in captured.out
    assert "Dashboards: 0 hits" in captured.out


def test_find_textual_select_empty(docker_grafana, capsys, caplog):

    # Run command and capture output.
    set_command("find foobar", "--select-dashboard=foo,bar")
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        captured = capsys.readouterr()

    # Verify output.
    assert (
        "GrafanaClientError: Client Error 404: Dashboard not found" in caplog.text
        or 'GrafanaClientError: Client Error 404: {"message":"Dashboard not found"}' in caplog.text
    )

    assert "Data Sources: 0 hits" in captured.out
    assert "Dashboards: 0 hits" in captured.out


def test_find_textual_dashboard_success(ldi_resources, capsys):

    # Only provision specific dashboard(s).
    ldi_resources(dashboards=["tests/grafana/dashboards/ldi-v27.json", "tests/grafana/dashboards/ldi-v33.json"])

    # Run command and capture output.
    set_command("find ldi_readings")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()

    # Verify output.
    assert 'Searching for expression "ldi_readings" at Grafana instance http://localhost:33333' in captured.out
    assert "Dashboards: 2 hits" in captured.out
    assert "luftdaten-info-generic-trend" in captured.out
    assert "Title luftdaten.info generic trend" in captured.out
    assert "Folder Testdrive" in captured.out
    assert "UID ioUrPwQiz" in captured.out
    assert "URL http://localhost:33333/d/ioUrPwQiz/luftdaten-info-generic-trend" in captured.out
    assert "dashboard.panels.[1].targets.[0].measurement: ldi_readings" in captured.out
    assert "dashboard.panels.[7].panels.[0].targets.[0].measurement: ldi_readings" in captured.out


def test_find_textual_datasource_success(ldi_resources, capsys):

    # Only provision specific dashboard(s).
    ldi_resources(dashboards=["tests/grafana/dashboards/ldi-v27.json", "tests/grafana/dashboards/ldi-v33.json"])

    # Run command and capture output.
    set_command("find ldi_v2")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()

    # Verify output.
    assert 'Searching for expression "ldi_v2" at Grafana instance http://localhost:33333' in captured.out

    assert "Data Sources: 1 hits" in captured.out
    assert "name: ldi_v2" in captured.out
    assert "database: ldi_v2" in captured.out

    assert "Dashboards: 1 hits" in captured.out
    assert "luftdaten-info-generic-trend" in captured.out
    assert "dashboard.panels.[1].datasource: ldi_v2" in captured.out
    assert "dashboard.panels.[7].panels.[0].datasource: ldi_v2" in captured.out


def test_find_tabular_dashboard_success(ldi_resources, capsys):

    # Only provision specific dashboard(s).
    ldi_resources(dashboards=["tests/grafana/dashboards/ldi-v27.json", "tests/grafana/dashboards/ldi-v33.json"])

    # Run command and capture output.
    set_command("find ldi_readings", "--format=tabular:pipe")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()

    # Verify output.
    assert 'Searching for expression "ldi_readings" at Grafana instance http://localhost:33333' in captured.out

    reference_table = """
| Type       | Name                             | Title                            | Folder    | UID       | Created              | Updated              | Created by   | Datasources                                                                           | URL                                                                 |
|:-----------|:---------------------------------|:---------------------------------|:----------|:----------|:---------------------|:---------------------|:-------------|:--------------------------------------------------------------------------------------|:--------------------------------------------------------------------|
| Dashboards | luftdaten-info-generic-trend-v27 | luftdaten.info generic trend v27 | Testdrive | ioUrPwQiz | xxxx-xx-xxTxx:xx:xxZ | xxxx-xx-xxTxx:xx:xxZ | admin        | -- Grafana --,ldi_v2,weatherbase                                                      | http://localhost:33333/d/ioUrPwQiz/luftdaten-info-generic-trend-v27 |
| Dashboards | luftdaten-info-generic-trend-v33 | luftdaten.info generic trend v33 | Testdrive | jpVsQxRja | xxxx-xx-xxTxx:xx:xxZ | xxxx-xx-xxTxx:xx:xxZ | admin        | -- Grafana --,{'type': 'influxdb', 'uid': 'PDF2762CDFF14A314'},{'uid': 'weatherbase'} | http://localhost:33333/d/jpVsQxRja/luftdaten-info-generic-trend-v33 |
    """.strip()

    output_table = captured.out[captured.out.find("| Type") :]
    output_table_normalized = re.sub(
        r"\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ", r"xxxx-xx-xxTxx:xx:xxZ", output_table
    ).strip()

    assert output_table_normalized == reference_table


def test_replace_dashboard_success(ldi_resources, capsys):

    # Only provision specific dashboard(s).
    ldi_resources(dashboards=["tests/grafana/dashboards/ldi-v27.json", "tests/grafana/dashboards/ldi-v33.json"])

    # Rename references from "ldi_v2" to "ldi_v3".
    set_command("replace ldi_v2 ldi_v3")
    grafana_wtf.commands.run()
    capsys.readouterr()

    # Verify new reference "ldi_v3".
    set_command("find ldi_v3")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()
    assert 'Searching for expression "ldi_v3" at Grafana instance http://localhost:33333' in captured.out

    # TODO: Expand renaming to data sources.
    assert "Data Sources: 0 hits" in captured.out
    # assert "name: ldi_v2" in captured.out
    # assert "database: ldi_v2" in captured.out

    assert "Dashboards: 1 hits" in captured.out
    assert "luftdaten-info-generic-trend-v27" in captured.out
    assert "Folder Testdrive" in captured.out
    assert "dashboard.panels.[1].datasource: ldi_v3" in captured.out
    assert "dashboard.panels.[7].panels.[0].datasource: ldi_v3" in captured.out

    # Rename back references from "ldi_v3" to "ldi_v2".
    set_command("replace ldi_v3 ldi_v2")
    grafana_wtf.commands.run()


def test_replace_dashboard_dry_run_success(ldi_resources, capsys):

    # Only provision specific dashboard(s).
    ldi_resources(dashboards=["tests/grafana/dashboards/ldi-v27.json", "tests/grafana/dashboards/ldi-v33.json"])

    # Rename references from "ldi_v2" to "ldi_v3".
    set_command("replace ldi_v2 ldi_v3 --dry-run")
    grafana_wtf.commands.run()
    capsys.readouterr()

    # Verify new reference "ldi_v3" does not exist, because it is still called "ldi_v2".
    set_command("find ldi_v3")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()

    assert "Dashboards: 0 hits" in captured.out


def test_log_empty(capsys, caplog):

    # Run command and capture output.
    set_command("log foobar")
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
    captured = capsys.readouterr()

    # Verify output.
    assert 'Aggregating edit history for Grafana dashboard "foobar" at http://localhost:33333' in caplog.text
    assert "[]" in captured.out


def test_log_json_success(ldi_resources, capsys, caplog):

    # Only provision specific dashboard(s).
    ldi_resources(dashboards=["tests/grafana/dashboards/ldi-v27.json", "tests/grafana/dashboards/ldi-v33.json"])

    # Run command and capture output.
    set_command("log ioUrPwQiz")
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
    captured = capsys.readouterr()

    # Verify output.
    assert 'Aggregating edit history for Grafana dashboard "ioUrPwQiz" at http://localhost:33333' in caplog.text

    reference = {
        # "datetime": "2021-09-29T17:32:23Z",
        "user": "admin",
        "message": "",
        "folder": "Testdrive",
        "title": "luftdaten.info generic trend v27",
        "version": 1,
        "url": "http://localhost:33333/d/ioUrPwQiz/luftdaten-info-generic-trend-v27",
    }

    history = json.loads(captured.out)
    item = history[-1]
    del item["datetime"]

    assert item == reference


def test_log_tabular_success(ldi_resources, capsys, caplog):

    # Only provision specific dashboard(s).
    ldi_resources(dashboards=["tests/grafana/dashboards/ldi-v27.json", "tests/grafana/dashboards/ldi-v33.json"])

    # Run command and capture output.
    set_command("log ioUrPwQiz", "--format=tabular:pipe")
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        captured = capsys.readouterr()

    # Verify output.
    assert 'Aggregating edit history for Grafana dashboard "ioUrPwQiz" at http://localhost:33333' in caplog.text

    reference = """
    | Notes: n/a<br/>[Testdrive » luftdaten.info generic trend v27](http://localhost:33333/d/ioUrPwQiz/luftdaten-info-generic-trend-v27) | User: admin<br/>Date: xxxx-xx-xxTxx:xx:xxZ      |
    """.strip()

    first_item_raw = str.splitlines(captured.out)[-1]
    first_item_normalized = re.sub("(.*)Date: .+|(.*)", r"\1Date: xxxx-xx-xxTxx:xx:xxZ      |\2", first_item_raw, 1)
    assert first_item_normalized == reference


def test_explore_datasources_used(create_datasource, create_dashboard, capsys, caplog):

    # Create two data sources and a dashboard which uses them.
    ds_foo = create_datasource(name="foo")
    ds_bar = create_datasource(name="bar")
    create_dashboard(mkdashboard(title="baz", datasources=[ds_foo, ds_bar]))

    # Compute breakdown.
    set_command("explore datasources", "--format=yaml")

    # Proof the output is correct.
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        assert "Found 2 data source(s)" in caplog.messages

    captured = capsys.readouterr()
    data = yaml.safe_load(captured.out)

    assert len(data["used"]) == 2
    assert len(data["unused"]) == 0

    # Results will be sorted by name, so `bar` comes first.
    assert data["used"][0]["datasource"]["name"] == "bar"
    assert data["used"][0]["datasource"]["type"] == "testdata"
    assert data["used"][1]["datasource"]["name"] == "foo"
    assert data["used"][1]["datasource"]["type"] == "testdata"


def test_explore_datasources_unused(create_datasource, capsys, caplog):

    # Create two datasources, which are not used by any dashboard.
    create_datasource(name="foo")
    create_datasource(name="bar")

    # Compute exploration.
    set_command("explore datasources", "--format=yaml")

    # Proof the output is correct.
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        assert "Found 2 unused data source(s)" in caplog.messages

    captured = capsys.readouterr()
    data = yaml.safe_load(captured.out)

    assert len(data["used"]) == 0
    assert len(data["unused"]) == 2

    assert data["unused"][0]["datasource"]["name"] == "bar"
    assert data["unused"][1]["datasource"]["name"] == "foo"


def test_explore_dashboards_grafana6(grafana_version, ldi_resources, capsys, caplog):
    """
    Grafana 6 does not have UIDs for data sources.
    """

    # Only for Grafana 6.
    if not grafana_version.startswith("6."):
        raise pytest.skip(f"Grafana 6 only")

    # Only provision specific dashboard.
    ldi_resources(dashboards=["tests/grafana/dashboards/ldi-v27.json"])

    # Compute exploration.
    set_command("explore dashboards", "--format=yaml")

    # Run command and capture YAML output.
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
    captured = capsys.readouterr()
    data = yaml.safe_load(captured.out)

    # Proof the output is correct.
    assert len(data) == 1
    dashboard = data[0]
    assert dashboard["dashboard"]["title"] == "luftdaten.info generic trend v27"
    assert dashboard["dashboard"]["uid"] == "ioUrPwQiz"
    assert dashboard["datasources"][0]["name"] == "ldi_v2"
    # Grafana 6 does not have UIDs for data sources.
    assert dashboard["datasources"][0]["uid"] is None
    assert dashboard["datasources"][0]["type"] == "influxdb"
    assert dashboard["datasources_missing"][0]["name"] == "weatherbase"
    assert dashboard["datasources_missing"][0]["uid"] is None
    assert dashboard["datasources_missing"][0]["type"] is None


def test_explore_dashboards_grafana7up(grafana_version, ldi_resources, capsys, caplog):
    """
    Grafana >= 7 has UIDs for data sources.
    """

    # Only for Grafana 7.
    if version.parse(grafana_version) < version.parse("7"):
        raise pytest.skip(f"Grafana >= 7 only")

    # Only provision specific dashboard.
    ldi_resources(dashboards=["tests/grafana/dashboards/ldi-v33.json"])

    # Compute exploration.
    set_command("explore dashboards", "--format=yaml")

    # Run command and capture YAML output.
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
    captured = capsys.readouterr()
    data = yaml.safe_load(captured.out)

    # Proof the output is correct.
    assert len(data) == 1
    dashboard = data[0]
    assert dashboard["dashboard"]["title"] == "luftdaten.info generic trend v33"
    assert dashboard["dashboard"]["uid"] == "jpVsQxRja"
    assert dashboard["datasources"][0]["name"] == "ldi_v2"
    # Grafana 7 has UIDs for data sources.
    assert dashboard["datasources"][0]["uid"] == "PDF2762CDFF14A314"
    assert dashboard["datasources"][0]["type"] == "influxdb"

    # FIXME: Those are coming from a bogus migration from schema version 27 to 33.
    assert dashboard["datasources_missing"][0]["name"] is None
    assert dashboard["datasources_missing"][0]["uid"] == "weatherbase"
    assert dashboard["datasources_missing"][0]["type"] is None


def test_explore_dashboards_empty_annotations(create_datasource, create_dashboard, capsys, caplog):

    # Create a dashboard with an anomalous value in the "annotations" slot.
    dashboard = mkdashboard(title="foo")
    dashboard["annotations"]["list"] = None
    create_dashboard(dashboard)

    # Compute breakdown.
    set_command("explore dashboards", "--format=yaml")

    # Proof the output is correct.
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        assert "Found 1 dashboard(s)" in caplog.messages

    captured = capsys.readouterr()
    data = yaml.safe_load(captured.out)

    # Proof the output is correct.
    assert len(data) == 1
    dashboard = data[0]
    assert dashboard["dashboard"]["title"] == "foo"
    assert len(dashboard["dashboard"]["uid"]) == 9
    assert "datasources" not in dashboard
    assert "datasources_missing" not in dashboard


def find_all_missing_datasources(data):
    missing_items = []
    for item in data:
        if "datasources_missing" in item:
            missing_items += item["datasources_missing"]
    return missing_items


def test_info(docker_grafana, capsys, caplog):

    # Which subcommand to test?
    set_command("info", "--format=yaml")

    # Run command and capture YAML output.
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
    captured = capsys.readouterr()
    data = yaml.safe_load(captured.out)

    # Proof the output is correct.
    assert list(data.keys()) == ["grafana", "statistics", "summary"]

    assert "version" in data["grafana"]
    assert "url" in data["grafana"]

    assert "dashboards" in data["summary"]
    assert "datasources" in data["summary"]
    assert "dashboard_panels" in data["summary"]
    assert "dashboard_annotations" in data["summary"]
    assert "dashboard_templating" in data["summary"]
