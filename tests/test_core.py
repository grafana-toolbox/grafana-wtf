from unittest.mock import Mock

from munch import Munch

from grafana_wtf.core import Indexer


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
