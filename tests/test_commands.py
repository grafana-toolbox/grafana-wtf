import json
import logging
import re
import shlex
import sys

import docopt
import pytest

import grafana_wtf.commands


def set_command(command, more_options=""):
    command = f'grafana-wtf --grafana-url="http://localhost:3000" {more_options} {command}'
    sys.argv = shlex.split(command)


def test_failure_grafana_url_missing():
    command = 'grafana-wtf find foobar'
    sys.argv = shlex.split(command)
    with pytest.raises(docopt.DocoptExit) as ex:
        grafana_wtf.commands.run()

    assert ex.match(re.escape('No Grafana URL given. Please use "--grafana-url" option or environment variable "GRAFANA_URL".'))


def test_find_empty(docker_grafana, capsys):
    set_command("find foobar")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()
    assert "Searching for expression \"foobar\" at Grafana instance http://localhost:3000" in captured.out
    assert "Data Sources: 0 hits" in captured.out
    assert "Dashboards: 0 hits" in captured.out


def test_find_select_empty(docker_grafana, capsys, caplog):
    set_command("find foobar", "--select-dashboard=foo,bar")
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        captured = capsys.readouterr()

        assert \
            'GrafanaClientError: Client Error 404: Dashboard not found' in caplog.text or \
            'GrafanaClientError: Client Error 404: {"message":"Dashboard not found"}' in caplog.text

        assert "Data Sources: 0 hits" in captured.out
        assert "Dashboards: 0 hits" in captured.out


def test_find_dashboard_success(docker_grafana, capsys):
    set_command("find ldi_readings")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()
    assert "Searching for expression \"ldi_readings\" at Grafana instance http://localhost:3000" in captured.out
    assert "Dashboards: 1 hits" in captured.out
    assert "luftdaten-info-generic-trend" in captured.out
    assert "Title luftdaten.info generic trend" in captured.out
    assert "Folder Testdrive" in captured.out
    assert "UID ioUrPwQiz" in captured.out
    assert "URL http://localhost:3000/d/ioUrPwQiz/luftdaten-info-generic-trend" in captured.out
    assert "dashboard.panels.[1].targets.[0].measurement: ldi_readings" in captured.out
    assert "dashboard.panels.[7].panels.[0].targets.[0].measurement: ldi_readings" in captured.out


def test_find_datasource_dashboard_success(docker_grafana, capsys):
    set_command("find ldi_v2")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()
    assert "Searching for expression \"ldi_v2\" at Grafana instance http://localhost:3000" in captured.out

    assert "Data Sources: 1 hits" in captured.out
    assert "name: ldi_v2" in captured.out
    assert "database: ldi_v2" in captured.out

    assert "Dashboards: 1 hits" in captured.out
    assert "luftdaten-info-generic-trend" in captured.out
    assert "dashboard.panels.[1].datasource: ldi_v2" in captured.out
    assert "dashboard.panels.[7].panels.[0].datasource: ldi_v2" in captured.out


def test_replace_dashboard_success(docker_grafana, capsys):

    grafana_url = "http://localhost:3000"

    # Rename references from "ldi_v2" to "ldi_v3".
    set_command("replace ldi_v2 ldi_v3")
    grafana_wtf.commands.run()
    capsys.readouterr()

    # Verify new reference "ldi_v3".
    set_command("find ldi_v3")
    grafana_wtf.commands.run()
    captured = capsys.readouterr()
    assert "Searching for expression \"ldi_v3\" at Grafana instance http://localhost:3000" in captured.out

    # TODO: Expand renaming to data sources.
    assert "Data Sources: 0 hits" in captured.out
    #assert "name: ldi_v2" in captured.out
    #assert "database: ldi_v2" in captured.out

    assert "Dashboards: 1 hits" in captured.out
    assert "luftdaten-info-generic-trend" in captured.out
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
        assert "Aggregating edit history for Grafana dashboard \"foobar\" at http://localhost:3000" in caplog.text
        assert "[]" in captured.out


def test_log_json(docker_grafana, capsys, caplog):
    set_command("log ioUrPwQiz")
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        captured = capsys.readouterr()
        assert "Aggregating edit history for Grafana dashboard \"ioUrPwQiz\" at http://localhost:3000" in caplog.text

        reference = {
            # "datetime": "2021-09-29T17:32:23Z",
            "user": "",
            "message": "",
            "folder": "Testdrive",
            "title": "luftdaten.info generic trend",
            "version": 1,
            "url": "http://localhost:3000/d/ioUrPwQiz/luftdaten-info-generic-trend"
        }

        history = json.loads(captured.out)
        item = history[-1]
        del item["datetime"]

        assert item == reference


def test_log_tabular_pipe(docker_grafana, capsys, caplog):
    set_command("log ioUrPwQiz", "--format=tabular:pipe")
    with caplog.at_level(logging.DEBUG):
        grafana_wtf.commands.run()
        captured = capsys.readouterr()
        assert "Aggregating edit history for Grafana dashboard \"ioUrPwQiz\" at http://localhost:3000" in caplog.text

        reference = """
        | Notes: n/a<br/>[Testdrive » luftdaten.info generic trend](http://localhost:3000/d/ioUrPwQiz/luftdaten-info-generic-trend)                                        | User: <br/>Date: xxxx-xx-xxTxx:xx:xxZ      |
        """.strip()

        first_item_raw = str.splitlines(captured.out)[-1]
        first_item_normalized = re.sub("(.*)Date: .+|(.*)", r"\1Date: xxxx-xx-xxTxx:xx:xxZ      |\2", first_item_raw, 1)
        assert first_item_normalized == reference