from unittest.mock import Mock, patch

import pytest
from munch import Munch

from grafana_wtf.core import Indexer, GrafanaWtf


def test_collect_datasource_items_variable_all():
    """
    Verify fix for `TypeError: unhashable type: 'list'` in `collect_datasource_items`.

    https://github.com/panodata/grafana-wtf/issues/62
    """
    node = Munch(
        {
            "current": Munch({"selected": True, "text": ["All"], "value": ["$__all"]}),
            "hide": 0,
            "includeAll": True,
            "multi": True,
            "name": "datasource",
            "options": [],
            "query": "prometheus",
            "queryValue": "",
            "refresh": 1,
            "regex": "/.*-storage$/",
            "skipUrlSync": False,
            "type": "datasource",
        }
    )
    engine_mock = Mock(
        scan_datasources=Mock(return_value=[]),
        scan_dashboards=Mock(return_value=[]),
        dashboard_details=Mock(return_value=[]),
    )
    indexer = Indexer(engine=engine_mock)
    result = indexer.collect_datasource_items([node])
    assert result == []


def test_connect_success():
    wtf = GrafanaWtf("https://play.grafana.org")
    health = wtf.health
    assert "commit" in health
    assert "version" in health
    assert health.database == "ok"


def test_connect_failure():
    wtf = GrafanaWtf("http://localhost:1234")
    with pytest.raises(ConnectionError) as ex:
        _ = wtf.health
    assert ex.match("The request to http://localhost:1234/api/health failed")


@patch("grafana_client.client.GrafanaClient.__getattr__")
def test_connect_version(mock_get):
    mock_get.return_value = Mock()
    mock_get.return_value.return_value = {"commit": "14e988bd22", "database": "ok", "version": "9.0.1"}
    wtf = GrafanaWtf("http://localhost:1234")
    assert wtf.version == "9.0.1"


def test_connect_non_json_response():
    wtf = GrafanaWtf("https://example.org/")
    with pytest.raises(ConnectionError) as ex:
        _ = wtf.health
    assert ex.match("The request to https://example.org/api/health failed: Client Error 404")
