from unittest.mock import Mock, patch

import pytest
from munch import Munch

from grafana_wtf.core import GrafanaEngine, GrafanaWtf, Indexer
from grafana_wtf.model import GrafanaDataModel


def test_collect_datasource_items_variable_all():
    """
    Verify fix for `TypeError: unhashable type: 'list'` in `collect_datasource_items`.

    https://github.com/grafana-toolbox/grafana-wtf/issues/62
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
    build_info = wtf.build_info
    assert "commit" in build_info
    assert "version" in build_info


def test_connect_failure():
    wtf = GrafanaWtf("http://localhost:1234")
    with pytest.raises(ConnectionError) as ex:
        _ = wtf.build_info
    assert ex.match("The request to http://localhost:1234/api/frontend/settings failed")


@patch("grafana_client.client.GrafanaClient.__getattr__")
def test_connect_version(mock_get):
    mock_get.return_value = Mock()
    mock_get.return_value.return_value = {"buildInfo": {"version": "9.0.1", "commit": "14e988bd22"}}
    wtf = GrafanaWtf("http://localhost:1234")
    assert wtf.version == "9.0.1"


def test_connect_non_json_response():
    wtf = GrafanaWtf("https://example.org/")
    with pytest.raises(ConnectionError) as ex:
        _ = wtf.build_info
    assert ex.match("The request to https://example.org/api/frontend/settings failed")


class TestScanDashboardsPagination:
    """Tests for pagination support in scan_dashboards."""

    def _create_engine_with_mock_grafana(self, search_side_effect):
        """Helper to create a GrafanaEngine with mocked grafana client."""
        engine = object.__new__(GrafanaEngine)
        engine.grafana = Mock()
        engine.grafana.search.search_dashboards = Mock(side_effect=search_side_effect)
        engine.grafana.dashboard.get_dashboard = Mock()
        engine.data = GrafanaDataModel()
        engine.progressbar = False
        engine.concurrency = None
        return engine

    def test_scan_dashboards_single_page(self):
        """When results are less than limit, only one page is fetched."""
        # 10 results, less than limit of 5000
        mock_results = [{"uid": f"dash-{i}", "title": f"Dashboard {i}"} for i in range(10)]

        engine = self._create_engine_with_mock_grafana(
            search_side_effect=[mock_results]
        )
        # Mock fetch_dashboards to avoid actual API calls
        engine.fetch_dashboards = Mock()

        engine.scan_dashboards()

        # Should only call search once
        assert engine.grafana.search.search_dashboards.call_count == 1
        engine.grafana.search.search_dashboards.assert_called_with(limit=5000, page=1)
        assert len(engine.data.dashboard_list) == 10

    def test_scan_dashboards_multiple_pages(self):
        """When first page is full, subsequent pages are fetched."""
        # Create mock data: page 1 has 5000 results, page 2 has 100 results
        page1_results = [{"uid": f"dash-{i}", "title": f"Dashboard {i}"} for i in range(5000)]
        page2_results = [{"uid": f"dash-{i}", "title": f"Dashboard {i}"} for i in range(5000, 5100)]

        engine = self._create_engine_with_mock_grafana(
            search_side_effect=[page1_results, page2_results]
        )
        engine.fetch_dashboards = Mock()

        engine.scan_dashboards()

        # Should call search twice
        assert engine.grafana.search.search_dashboards.call_count == 2
        assert len(engine.data.dashboard_list) == 5100

    def test_scan_dashboards_empty_results(self):
        """When no dashboards exist, handle empty response correctly."""
        engine = self._create_engine_with_mock_grafana(
            search_side_effect=[[]]
        )
        engine.fetch_dashboards = Mock()

        engine.scan_dashboards()

        assert engine.grafana.search.search_dashboards.call_count == 1
        assert len(engine.data.dashboard_list) == 0

    def test_scan_dashboards_exact_limit_boundary(self):
        """When results exactly equal limit, fetch next (empty) page."""
        # Page 1 has exactly 5000 results, page 2 is empty
        page1_results = [{"uid": f"dash-{i}", "title": f"Dashboard {i}"} for i in range(5000)]
        page2_results = []

        engine = self._create_engine_with_mock_grafana(
            search_side_effect=[page1_results, page2_results]
        )
        engine.fetch_dashboards = Mock()

        engine.scan_dashboards()

        # Should call search twice (second call discovers no more results)
        assert engine.grafana.search.search_dashboards.call_count == 2
        assert len(engine.data.dashboard_list) == 5000
