# -*- coding: utf-8 -*-
# (c) 2021 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import dataclasses
from collections import OrderedDict
from typing import Dict, List, Optional
from urllib.parse import urljoin

from munch import Munch


@dataclasses.dataclass
class GrafanaDataModel:
    admin_stats: Optional[Dict] = dataclasses.field(default_factory=dict)
    dashboards: Optional[List[Munch]] = dataclasses.field(default_factory=list)
    dashboard_list: Optional[List[Munch]] = dataclasses.field(default_factory=list)
    datasources: Optional[List[Munch]] = dataclasses.field(default_factory=list)
    folders: Optional[List[Munch]] = dataclasses.field(default_factory=list)
    organizations: Optional[List[Munch]] = dataclasses.field(default_factory=list)
    users: Optional[List[Munch]] = dataclasses.field(default_factory=list)
    teams: Optional[List[Munch]] = dataclasses.field(default_factory=list)
    annotations: Optional[List[Munch]] = dataclasses.field(default_factory=list)
    snapshots: Optional[List[Munch]] = dataclasses.field(default_factory=list)
    notifications: Optional[List[Munch]] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class DashboardDetails:

    dashboard: Dict

    @property
    def panels(self) -> List:
        return self.dashboard.dashboard.get("panels", [])

    @property
    def annotations(self) -> List:
        return self.dashboard.dashboard.get("annotations", {}).get("list", [])

    @property
    def templating(self) -> List:
        return self.dashboard.dashboard.get("templating", {}).get("list", [])


@dataclasses.dataclass
class DatasourceItem:
    uid: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: any):
        if isinstance(payload, Munch):
            payload = dict(payload)
        if isinstance(payload, dict):
            return cls(**payload)
        if isinstance(payload, str):
            return cls(name=payload)
        raise TypeError(f"Unknown payload type for DatasourceItem: {type(payload)}")


@dataclasses.dataclass
class DatasourceExplorationItem:
    datasource: Munch
    used_in: List[Munch]
    grafana_url: str

    def format_compact(self):
        dsshort = OrderedDict(
            uid=self.datasource.get("uid"),
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
                uid=datasource.get("uid"),
                name=datasource.name,
                type=datasource.type,
                url=datasource.url,
            )
            item["datasources"].append(dsshort)
        return item
