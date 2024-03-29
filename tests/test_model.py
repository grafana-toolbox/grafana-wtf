import re

import pytest
from munch import Munch

from grafana_wtf.model import DatasourceItem

DATA = dict(uid="foo", name="bar", type="baz", url="qux")


def test_datasource_item_basic():
    item = DatasourceItem(**DATA)
    assert item.uid == "foo"


def test_datasource_item_dict_success():
    item = DatasourceItem.from_payload(DATA)
    assert item.uid == "foo"


def test_datasource_item_munch():
    item = DatasourceItem.from_payload(Munch(**DATA))
    assert item.uid == "foo"


def test_datasource_item_str():
    item = DatasourceItem.from_payload("Hotzenplotz")
    assert item.uid is None
    assert item.name == "Hotzenplotz"


def test_datasource_item_dict_unknown_attribute():
    mydata = DATA.copy()
    mydata.update({"more": "data"})
    with pytest.raises(TypeError) as ex:
        DatasourceItem.from_payload(mydata)
    assert ex.match(re.escape("__init__() got an unexpected keyword argument 'more'"))


def test_datasource_item_dict_compensate_datasource():
    """
    Validate that the `datasource` attribute is ignored.

    TypeError: DatasourceItem.__init__() got an unexpected keyword argument 'datasource'
    https://github.com/panodata/grafana-wtf/issues/110
    """
    mydata = DATA.copy()
    mydata.update({"datasource": "unknown"})
    with pytest.warns(UserWarning) as record:
        item = DatasourceItem.from_payload(mydata)
        assert item.uid == "foo"

    # Check that only one warning was raised.
    assert len(record) == 1

    # Check that the message matches.
    assert "The `datasource` attribute is ignored for the time being" in record[0].message.args[0]
