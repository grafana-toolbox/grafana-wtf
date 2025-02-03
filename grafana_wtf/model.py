# -*- coding: utf-8 -*-
# (c) 2021 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import dataclasses
import logging
import warnings
from collections import OrderedDict
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from munch import Munch

logger = logging.getLogger(__name__)


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
class DashboardDataDetails:
    """
    Manage details concerned about "data"-relevant information,
    a subset of the complete bunch of dashboard information.
    """

    panels: List[Dict]
    annotations: List[Dict]
    templating: List[Dict]

    def to_munch(self):
        return Munch(panels=self.panels, annotations=self.annotations, templating=self.templating)

    @classmethod
    def from_dashboard_details(cls, dbdetails: DashboardDetails):
        ds_panels = cls.collect_data_nodes(dbdetails.panels)
        ds_annotations = cls.collect_data_nodes(dbdetails.annotations)
        ds_templating = cls.collect_data_nodes(dbdetails.templating)

        # Inline panel information into data details.
        targets = []
        for panel in ds_panels:
            panel_item = cls._format_panel_compact(panel)
            if "targets" in panel:
                for target in panel.targets:
                    target["_panel"] = panel_item
                    targets.append(target)

        return cls(panels=targets, annotations=ds_annotations, templating=ds_templating)

    @staticmethod
    def collect_data_nodes(element):
        """
        Select all element nodes which have a "datasource" attribute.
        """
        element = element or []
        items = []

        def add(item):
            if item is not None and item not in items:
                items.append(item)

        for node in element:
            if "datasource" in node and node["datasource"]:
                add(node)

        return items

    @staticmethod
    def _format_panel_compact(panel):
        """
        Return a compact representation of panel information.
        """
        attributes = ["id", "title", "type", "datasource"]
        data = OrderedDict()
        for attribute in attributes:
            data[attribute] = panel.get(attribute)
        return data

    @staticmethod
    def _format_data_node_compact(item: Dict) -> Dict:
        """
        Return a compact representation of an element concerned about data.
        """
        data = OrderedDict()
        data["datasource"] = item.get("datasource")
        data["type"] = item.get("type")
        for key, value in item.items():
            if "query" in key.lower():
                data[key] = value
        return data

    def queries_only(self):
        """
        Return a representation of data details information.

        Only where query expressions are present.
        """
        # All attributes containing query-likes.
        attributes_query_likes = ["expr", "jql", "query", "rawSql", "target"]

        attributes = [
            # Carry over datasource and panel references for informational purposes.
            "datasource",
            "_panel",
        ] + attributes_query_likes

        def transform(section):
            new_items = []
            for item in section:
                new_item = OrderedDict()
                for key, value in item.items():
                    if key in attributes:
                        new_item[key] = value
                if any(attr in attributes_query_likes for attr in new_item.keys()):
                    # Filter annotations without any value.
                    if "target" in new_item and isinstance(new_item["target"], dict):
                        if new_item["target"].get("type") == "dashboard":
                            continue
                    # Unnest items with nested "query" slot.
                    for slot in ["query", "target"]:
                        if (
                            slot in new_item
                            and isinstance(new_item[slot], dict)
                            and "query" in new_item[slot]
                        ):
                            new_item["query"] = new_item[slot]["query"]
                    new_items.append(new_item)
            return new_items

        return DashboardDataDetails(
            panels=transform(self.panels),
            annotations=transform(self.annotations),
            templating=transform(self.templating),
        )


@dataclasses.dataclass
class DatasourceItem:
    """
    Represent a datasource reference within a panel, annotation, or templating (variable).
    """

    uid: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    default: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: any):
        if isinstance(payload, Munch):
            payload = dict(payload)
        if isinstance(payload, dict):
            cls.validate(payload)
            return cls(**payload)
        if isinstance(payload, str):
            return cls(name=payload)
        raise TypeError(f"Unknown payload type for DatasourceItem: {type(payload)}")

    @classmethod
    def validate(cls, data: dict):
        if "datasource" in data:
            warnings.warn(
                f"""
The `datasource` attribute is ignored for the time being.

See also: https://github.com/grafana-toolbox/grafana-wtf/issues/110

Please report back this occurrence to the grafana-wtf issue tracker,
so the maintainers can improve the situation.

The context of this error is in `DatasourceItem`, using this ingress data:
{data}
""".strip(),
                UserWarning,
                stacklevel=2,
            )
            del data["datasource"]


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

    def format(self, with_data_details: bool = False, queries_only: bool = False):
        """
        Generate a representation from selected information.

        - dashboard
        - datasources
        - details
            - panels/targets
            - annotations
            - templating
        """
        dbshort = OrderedDict(
            title=self.dashboard.dashboard.title,
            uid=self.dashboard.dashboard.uid,
            path=self.dashboard.meta.url,
            url=urljoin(self.grafana_url, self.dashboard.meta.url),
        )

        dsshort = []
        for datasource in self.datasources:
            item = OrderedDict(
                uid=datasource.get("uid"),
                name=datasource.name,
                type=datasource.type,
                url=datasource.url,
            )
            dsshort.append(item)

        data = Munch(dashboard=dbshort, datasources=dsshort)
        if with_data_details:
            details = self.collect_data_details(queries_only=queries_only)
            if not details.panels and not details.annotations and not details.templating:
                return None
            data.details = details.to_munch()
        return data

    def collect_data_details(self, queries_only: bool = False):
        """
        Collect details concerned about data from dashboard information.
        """

        dbdetails = DashboardDetails(dashboard=self.dashboard)
        dbdatadetails = DashboardDataDetails.from_dashboard_details(dbdetails)
        if queries_only:
            dbdatadetails = dbdatadetails.queries_only()
        return dbdatadetails
