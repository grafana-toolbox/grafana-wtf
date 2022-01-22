import json
import logging
import operator
import re
import shlex
import sys

import docopt
import pytest
import yaml

import grafana_wtf.commands


def set_command(command, more_options=""):
    command = f'grafana-wtf --grafana-url="http://localhost:3000" {more_options} {command}'
    sys.argv = shlex.split(command)


def test_failure_grafana_url_missing():
    command = "grafana-wtf find foobar"
    sys.argv = shlex.split(command)
    with pytest.raises(docopt.DocoptExit) as ex:
        grafana_wtf.commands.run()

    assert ex.match(
        re.escape('No Grafana URL given. Please use "--grafana-url" option or environment variable "GRAFANA_URL".')
    )


def test_find_textual_empty(docker_grafana, capsys):
    set_command("find foobar")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()
    assert 'Searching for expression "foobar" at Grafana instance http://localhost:3000' in captured.out
    assert "Data Sources: 0 hits" in captured.out
    assert "Dashboards: 0 hits" in captured.out


def test_find_textual_select_empty(docker_grafana, capsys, caplog):
    set_command("find foobar", "--select-dashboard=foo,bar")
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        captured = capsys.readouterr()

        assert (
            "GrafanaClientError: Client Error 404: Dashboard not found" in caplog.text
            or 'GrafanaClientError: Client Error 404: {"message":"Dashboard not found"}' in caplog.text
        )

        assert "Data Sources: 0 hits" in captured.out
        assert "Dashboards: 0 hits" in captured.out


def test_find_textual_dashboard_success(docker_grafana, capsys):
    set_command("find ldi_readings")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()
    assert 'Searching for expression "ldi_readings" at Grafana instance http://localhost:3000' in captured.out
    assert "Dashboards: 2 hits" in captured.out
    assert "luftdaten-info-generic-trend" in captured.out
    assert "Title luftdaten.info generic trend" in captured.out
    assert "Folder Testdrive" in captured.out
    assert "UID ioUrPwQiz" in captured.out
    assert "URL http://localhost:3000/d/ioUrPwQiz/luftdaten-info-generic-trend" in captured.out
    assert "dashboard.panels.[1].targets.[0].measurement: ldi_readings" in captured.out
    assert "dashboard.panels.[7].panels.[0].targets.[0].measurement: ldi_readings" in captured.out


def test_find_textual_datasource_success(docker_grafana, capsys):
    set_command("find ldi_v2")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()
    assert 'Searching for expression "ldi_v2" at Grafana instance http://localhost:3000' in captured.out

    assert "Data Sources: 1 hits" in captured.out
    assert "name: ldi_v2" in captured.out
    assert "database: ldi_v2" in captured.out

    assert "Dashboards: 1 hits" in captured.out
    assert "luftdaten-info-generic-trend" in captured.out
    assert "dashboard.panels.[1].datasource: ldi_v2" in captured.out
    assert "dashboard.panels.[7].panels.[0].datasource: ldi_v2" in captured.out


def test_find_tabular_dashboard_success(docker_grafana, capsys):
    set_command("find ldi_readings", "--format=tabular:pipe")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()

    assert 'Searching for expression "ldi_readings" at Grafana instance http://localhost:3000' in captured.out

    reference_table = """
| Type       | Name                             | Title                            | Folder    | UID       | Created              | Updated              | Created by   | Datasources                                                                           | URL                                                                |
|:-----------|:---------------------------------|:---------------------------------|:----------|:----------|:---------------------|:---------------------|:-------------|:--------------------------------------------------------------------------------------|:-------------------------------------------------------------------|
| Dashboards | luftdaten-info-generic-trend-v27 | luftdaten.info generic trend v27 | Testdrive | ioUrPwQiz | xxxx-xx-xxTxx:xx:xxZ | xxxx-xx-xxTxx:xx:xxZ | Anonymous    | -- Grafana --,ldi_v2,weatherbase                                                      | http://localhost:3000/d/ioUrPwQiz/luftdaten-info-generic-trend-v27 |
| Dashboards | luftdaten-info-generic-trend-v33 | luftdaten.info generic trend v33 | Testdrive | jpVsQxRja | xxxx-xx-xxTxx:xx:xxZ | xxxx-xx-xxTxx:xx:xxZ | Anonymous    | -- Grafana --,{'type': 'influxdb', 'uid': 'PDF2762CDFF14A314'},{'uid': 'weatherbase'} | http://localhost:3000/d/jpVsQxRja/luftdaten-info-generic-trend-v33 |
    """.strip()

    output_table = captured.out[captured.out.find("| Type") :]
    output_table_normalized = re.sub(
        r"\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ", r"xxxx-xx-xxTxx:xx:xxZ", output_table
    ).strip()

    assert output_table_normalized == reference_table


def test_replace_dashboard_success(docker_grafana, capsys):

    # Rename references from "ldi_v2" to "ldi_v3".
    set_command("replace ldi_v2 ldi_v3")
    grafana_wtf.commands.run()
    capsys.readouterr()

    # Verify new reference "ldi_v3".
    set_command("find ldi_v3")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()
    assert 'Searching for expression "ldi_v3" at Grafana instance http://localhost:3000' in captured.out

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


def test_log_empty(docker_grafana, capsys, caplog):
    set_command("log foobar")
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        captured = capsys.readouterr()
        assert 'Aggregating edit history for Grafana dashboard "foobar" at http://localhost:3000' in caplog.text
        assert "[]" in captured.out


def test_log_json_success(docker_grafana, capsys, caplog):
    set_command("log ioUrPwQiz")
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        captured = capsys.readouterr()
        assert 'Aggregating edit history for Grafana dashboard "ioUrPwQiz" at http://localhost:3000' in caplog.text

        reference = {
            # "datetime": "2021-09-29T17:32:23Z",
            "user": "",
            "message": "",
            "folder": "Testdrive",
            "title": "luftdaten.info generic trend v27",
            "version": 1,
            "url": "http://localhost:3000/d/ioUrPwQiz/luftdaten-info-generic-trend-v27",
        }

        history = json.loads(captured.out)
        item = history[-1]
        del item["datetime"]

        assert item == reference


def test_log_tabular_success(docker_grafana, capsys, caplog):
    set_command("log ioUrPwQiz", "--format=tabular:pipe")
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        captured = capsys.readouterr()
        assert 'Aggregating edit history for Grafana dashboard "ioUrPwQiz" at http://localhost:3000' in caplog.text

        reference = """
        | Notes: n/a<br/>[Testdrive » luftdaten.info generic trend v27](http://localhost:3000/d/ioUrPwQiz/luftdaten-info-generic-trend-v27)                                        | User: <br/>Date: xxxx-xx-xxTxx:xx:xxZ      |
        """.strip()

        first_item_raw = str.splitlines(captured.out)[-1]
        first_item_normalized = re.sub("(.*)Date: .+|(.*)", r"\1Date: xxxx-xx-xxTxx:xx:xxZ      |\2", first_item_raw, 1)
        assert first_item_normalized == reference


def test_explore_datasources(docker_grafana, create_datasource, capsys, caplog):

    # Create a datasource, which is not used by any dashboard.
    create_datasource(name="foo", type="foo", access="foo")
    create_datasource(name="bar", type="bar", access="bar")

    # Compute exploration.
    set_command("explore datasources", "--format=yaml")

    # Proof the output is correct.
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        assert "Found 2 unused data source(s)" in caplog.messages

    captured = capsys.readouterr()
    data = yaml.safe_load(captured.out)

    assert len(data["used"]) >= 1
    assert len(data["unused"]) >= 2

    assert data["unused"][0]["datasource"]["name"] == "bar"
    assert data["unused"][1]["datasource"]["name"] == "foo"


def test_explore_dashboards(docker_grafana, create_datasource, capsys, caplog):

    # Compute exploration.
    set_command("explore dashboards", "--format=yaml")

    # Run command and capture YAML output.
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
    captured = capsys.readouterr()
    data = yaml.safe_load(captured.out)

    # Proof the output is correct.
    assert len(data) >= 1

    missing = find_all_missing_datasources(data)

    # FIXME: Those are coming from a bogus migration from schema version 27 to 33.
    assert missing[0]["name"] == "weatherbase"
    # assert missing[1]["uid"] == "weatherbase"


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
