import os
from collections import OrderedDict
from grafana_wtf.report import WtfReport
from tabulate import tabulate
from jsonpath_rw import parse


class TabularReport(WtfReport):
    def __init__(self, grafana_url, tblfmt="psql", verbose=False):
        self.format = tblfmt
        super().__init__(grafana_url, verbose=verbose)

    def output_items(self, label, items, url_callback):
        items_rows = [
            {
                "type": label,
                "name": self.get_item_name(item),
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
        bibdata["Creation date"] = f"{item.data.meta.created}"
        bibdata["created by"] = item.data.meta.createdBy
        bibdata["last update date"] = f"{item.data.meta.updated}"
        if "PYTEST_CURRENT_TEST" not in os.environ:
            bibdata["updated by"] = item.data.meta.updatedBy
        _finder = parse("$..datasource")
        _datasources = _finder.find(item)
        bibdata["datasources"] = ",".join(
            sorted(set([str(_ds.value) for _ds in _datasources if _ds.value])) if _datasources else ""
        )
        bibdata.update(kwargs)
        return bibdata
