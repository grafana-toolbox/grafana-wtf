import os
from collections import OrderedDict

from jsonpath_rw import parse
from munch import Munch
from tabulate import tabulate

from grafana_wtf.report import WtfReport


class TabularReport(WtfReport):
    def __init__(self, grafana_url, tblfmt="psql", verbose=False):
        self.format = tblfmt
        super().__init__(grafana_url, verbose=verbose)

    def output_items(self, label, items, url_callback):
        items_rows = [
            {
                "Type": label,
                "Name": self.get_item_name(item),
                **self.get_bibdata_dict(item, URL=url_callback(item)),
            }
            for item in items
        ]
        print(tabulate(items_rows, headers="keys", tablefmt=self.format))

    def get_bibdata_dict(self, item, **kwargs):

        # Sanity checks.
        if "dashboard" not in item.data:
            return {"data_source_type": item.data.type} if "type" in item.data else {}
        bibdata = OrderedDict()
        bibdata["Title"] = item.data.dashboard.title
        bibdata["Folder"] = item.data.meta.folderTitle
        bibdata["UID"] = item.data.dashboard.uid
        bibdata["Created"] = f"{item.data.meta.created}"
        bibdata["Updated"] = f"{item.data.meta.updated}"
        bibdata["Created by"] = item.data.meta.createdBy

        # FIXME: The test fixtures are currently not deterministic,
        #        because Grafana is not cleared on each test case.
        if "PYTEST_CURRENT_TEST" not in os.environ:
            bibdata["Updated by"] = item.data.meta.updatedBy

        bibdata["Datasources"] = ",".join(map(str, self.get_datasources(item)))
        bibdata.update(kwargs)
        return bibdata

    def get_datasources(self, item):

        # Query datasources.
        _finder = parse("$..datasource")
        _datasources = _finder.find(item)

        # Compute unique list of datasources.
        datasources = []
        for _ds in _datasources:
            if not _ds.value:
                continue
            if isinstance(_ds.value, Munch):
                value = dict(_ds.value)
            else:
                value = str(_ds.value)
            if value not in datasources:
                datasources.append(value)

        return datasources
