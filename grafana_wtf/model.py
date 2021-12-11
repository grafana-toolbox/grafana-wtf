import dataclasses
from typing import List

from munch import Munch
from collections import OrderedDict
from urllib.parse import urljoin


@dataclasses.dataclass
class DatasourceExplorationItem:
    datasource: Munch
    used_in: List[Munch]
    grafana_url: str

    def format_compact(self):
        dsshort = OrderedDict(
            name=self.datasource.name,
            type=self.datasource.type,
            url=self.datasource.url,
        )
        item = OrderedDict(datasource=dsshort)
        for dashboard in self.used_in:
            item.setdefault("dashboards", [])
            dbshort = OrderedDict(
                title=dashboard.dashboard.title,
                uid=dashboard.dashboard.uid,
                path=dashboard.meta.url,
                url=urljoin(self.grafana_url, dashboard.meta.url),
            )
            item["dashboards"].append(dbshort)
        return item


@dataclasses.dataclass
class DashboardExplorationItem:
    dashboard: Munch
    datasources: List[Munch]
    grafana_url: str

    def format_compact(self):
        dbshort = OrderedDict(
            title=self.dashboard.dashboard.title,
            uid=self.dashboard.dashboard.uid,
            path=self.dashboard.meta.url,
            url=urljoin(self.grafana_url, self.dashboard.meta.url),
        )
        item = OrderedDict(dashboard=dbshort)
        for datasource in self.datasources:
            item.setdefault("datasources", [])
            dsshort = OrderedDict(
                name=datasource.name,
                type=datasource.type,
                url=datasource.url,
            )
            item["datasources"].append(dsshort)
        return item
