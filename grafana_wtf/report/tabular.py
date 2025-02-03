import os
from collections import OrderedDict

from jsonpath_rw import parse
from munch import Munch
from tabulate import tabulate

from grafana_wtf.report.textual import TextualSearchReport


def get_table_format(output_format):
    tablefmt = None
    if output_format is not None and output_format.startswith("tabular"):
        try:
            tablefmt = output_format.split(":")[1]
        except Exception:
            tablefmt = "psql"

    return tablefmt


class TabularSearchReport(TextualSearchReport):
    def __init__(self, grafana_url, tblfmt="psql", verbose=False):
        self.format = tblfmt
        super().__init__(grafana_url, verbose=verbose)

    def output_items(self, label, items, url_callback):
        items_rows = self.get_output_items(label, items, url_callback)
        print(tabulate(items_rows, headers="keys", tablefmt=self.format))

    def get_output_items(self, label, items, url_callback):
        return [
            {
                "Type": label,
                "Name": self.get_item_name(item),
                **self.get_bibdata_dict(item, URL=url_callback(item)),
            }
            for item in items
        ]

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


class TabularEditHistoryReport:
    def __init__(self, data):
        self.data = data

    def render(self, output_format: str):
        table_format = get_table_format(output_format)
        entries = self.compact_table(self.to_table(self.data), output_format)
        return tabulate(entries, headers="keys", tablefmt=table_format)

    @staticmethod
    def to_table(entries):
        for entry in entries:
            item = entry
            name = item["title"]
            if item["folder"]:
                name = item["folder"].strip() + " » " + name.strip()
            item["name"] = name.strip(" 🤓")
            # del item['url']
            del item["folder"]
            del item["title"]
            del item["version"]
            yield item

    @staticmethod
    def compact_table(entries, format):  # noqa: A002
        seperator = "\n"
        if format.endswith("pipe"):
            seperator = "<br/>"
        for entry in entries:
            item = OrderedDict()
            if format.endswith("pipe"):
                link = "[{}]({})".format(entry["name"], entry["url"])
            else:
                link = "Name: {}\nURL: {}".format(entry["name"], entry["url"])
            item["Dashboard"] = seperator.join(
                [
                    "Notes: {}".format(entry["message"].capitalize() or "n/a"),
                    link,
                ]
            )
            item["Update"] = seperator.join(
                [
                    "User: {}".format(entry["user"]),
                    "Date: {}".format(entry["datetime"]),
                ]
            )
            yield item
