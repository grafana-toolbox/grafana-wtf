# -*- coding: utf-8 -*-
# (c) 2019-2022 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import asyncio
import dataclasses
import json
import logging
import warnings
from collections import OrderedDict
from concurrent.futures.thread import ThreadPoolExecutor
from urllib.parse import parse_qs, urljoin, urlparse

import colored
import niquests
import requests_cache
from grafana_client.api import GrafanaApi
from grafana_client.client import GrafanaClientError, GrafanaUnauthorizedError
from munch import Munch, munchify
from tqdm import tqdm
from tqdm.contrib.logging import tqdm_logging_redirect
from urllib3.exceptions import InsecureRequestWarning
from verlib2.packaging.version import Version

from grafana_wtf import __appname__, __version__
from grafana_wtf.compat import CachedSession
from grafana_wtf.model import (
    DashboardDetails,
    DashboardExplorationItem,
    DatasourceExplorationItem,
    DatasourceItem,
    GrafanaDataModel,
)
from grafana_wtf.util import JsonPathFinder, as_bool, to_list

log = logging.getLogger(__name__)


class GrafanaEngine:
    # Configure a larger HTTP request pool.
    # TODO: Review the pool settings and eventually adjust according
    #       to concurrency level or other parameters.
    # https://urllib3.readthedocs.io/en/latest/advanced-usage.html#customizing-pool-behavior
    # https://laike9m.com/blog/requests-secret-pool_connections-and-pool_maxsize,89/
    session_args = dict(pool_connections=100, pool_maxsize=100, retries=5)

    # The HTTP `User-Agent` header value.
    user_agent = f"{__appname__}/{__version__}"

    def __init__(self, grafana_url, grafana_token=None):
        self.grafana_url = grafana_url
        self.grafana_token = grafana_token

        self.concurrency = 5

        self.grafana = self.grafana_client_factory(
            self.grafana_url, grafana_token=self.grafana_token
        )
        self.set_user_agent()
        self.data = GrafanaDataModel()
        self.finder = JsonPathFinder()

        self.taqadum = None
        self.debug = log.getEffectiveLevel() == logging.DEBUG
        self.progressbar = not self.debug

    def set_session(self, session):
        self.grafana.client.s = session

    def enable_cache(self, expire_after=60, drop_cache=False):
        if expire_after is None:
            log.info("Response cache will never expire (infinite caching)")
        elif expire_after == 0:
            log.info("Response cache will expire immediately (expire_after=0)")
        else:
            log.info(f"Response cache will expire after {expire_after} seconds")

        session = CachedSession(
            cache_name=__appname__,
            expire_after=expire_after,
            use_cache_dir=True,
            wal=True,
            **self.session_args,
        )
        self.set_session(session)
        self.set_user_agent()

        log.info(f"Response cache database: {session.cache.db_path}")
        if drop_cache:
            log.info("Dropping response cache")
            self.clear_cache()

        return self

    def clear_cache(self):
        log.info("Clearing cache")
        requests_cache.clear()

    def enable_concurrency(self, concurrency):
        self.concurrency = concurrency

    @classmethod
    def grafana_client_factory(cls, grafana_url, grafana_token=None):
        url = urlparse(grafana_url)

        # Grafana API Key auth
        if grafana_token:
            auth = grafana_token

        # HTTP basic auth
        else:
            username = url.username or "admin"
            password = url.password or "admin"
            auth = (username, password)

        verify = as_bool(parse_qs(url.query).get("verify", [True])[0])
        if verify is False:
            warnings.filterwarnings("ignore", category=InsecureRequestWarning)
        grafana = GrafanaApi(
            auth,
            protocol=url.scheme,
            host=url.hostname,
            port=url.port,
            url_path_prefix=url.path.lstrip("/"),
            verify=verify,
        )

        # Configure HTTP session to use a larger HTTP request pool.
        grafana.client.s = niquests.Session(**cls.session_args)

        return grafana

    def set_user_agent(self):
        self.grafana.client.s.headers["User-Agent"] = self.user_agent

    def start_progressbar(self, total):
        if self.progressbar:
            with tqdm_logging_redirect():
                self.taqadum = tqdm(total=total)

    def scan_common(self):
        self.scan_dashboards()
        self.scan_datasources()

    def scan_all(self):
        self.scan_common()
        self.scan_admin_stats()
        self.scan_folders()
        self.scan_organizations()
        self.scan_users()
        self.scan_teams()
        self.scan_annotations()
        self.scan_snapshots()
        self.scan_notifications()

    def scan_admin_stats(self):
        self.data.admin_stats = self.grafana.admin.stats()

    def scan_folders(self):
        self.data.folders = self.grafana.folder.get_all_folders()

    def scan_organizations(self):
        self.data.organizations = self.grafana.organizations.list_organization()

    def scan_users(self):
        self.data.users = self.grafana.users.search_users()

    def scan_teams(self):
        self.data.teams = self.grafana.teams.search_teams()

    def scan_annotations(self):
        self.data.annotations = self.grafana.annotations.get_annotation()

    def scan_snapshots(self):
        self.data.snapshots = self.grafana.snapshots.get_dashboard_snapshots()

    def scan_notifications(self):
        if Version(self.grafana.version) < Version("11"):
            self.data.notifications = self.grafana.notifications.lookup_channels()
        else:
            warnings.warn(
                "Notification channel scanning support for Grafana 11 is not implemented yet",
                UserWarning,
                stacklevel=2,
            )

    def scan_datasources(self):
        log.info("Scanning datasources")
        try:
            self.data.datasources = munchify(self.grafana.datasource.list_datasources())
            log.info("Found {} data source(s)".format(len(self.data.datasources)))
            return self.data.datasources
        except GrafanaClientError as ex:
            message = "{name}: {ex}".format(name=ex.__class__.__name__, ex=ex)
            log.error(self.get_red_message(message))
            if isinstance(ex, GrafanaUnauthorizedError):
                log.error(
                    self.get_red_message(
                        "Please use --grafana-token or GRAFANA_TOKEN "
                        "for authenticating with Grafana"
                    )
                )

    def scan_dashboards(self, dashboard_uids=None):
        log.info("Scanning dashboards")
        try:
            if dashboard_uids is not None:
                for uid in dashboard_uids:
                    log.info(f"Fetching dashboard by uid {uid}")
                    try:
                        dashboard = self.grafana.dashboard.get_dashboard(uid)
                        self.data.dashboard_list.append(dashboard["dashboard"])
                    except GrafanaClientError as ex:
                        self.handle_grafana_error(ex)
                        continue
            else:
                self.data.dashboard_list = self.grafana.search.search_dashboards(limit=5000)
            log.info("Found {} dashboard(s)".format(len(self.data.dashboard_list)))

        except GrafanaClientError as ex:
            self.handle_grafana_error(ex)
            return None

        if self.progressbar:
            self.start_progressbar(len(self.data.dashboard_list))

        if self.concurrency is None or self.concurrency <= 1:
            self.fetch_dashboards()
        else:
            self.fetch_dashboards_parallel()

        if self.progressbar:
            self.taqadum.close()

        # Improve determinism by returning stable sort order.
        self.data.dashboards = munchify(
            sorted(self.data.dashboards, key=lambda x: x["dashboard"]["uid"])
        )

        return self.data.dashboards

    def handle_grafana_error(self, ex):
        message = "{name}: {ex}".format(name=ex.__class__.__name__, ex=ex)
        message = colored.stylize(message, colored.fg("red") + colored.attr("bold"))
        log.error(self.get_red_message(message))
        if isinstance(ex, GrafanaUnauthorizedError):
            log.error(
                self.get_red_message(
                    "Please use --grafana-token or GRAFANA_TOKEN for authenticating with Grafana"
                )
            )

    def fetch_dashboard(self, dashboard_info):
        log.debug(f'Fetching dashboard "{dashboard_info["title"]}" ({dashboard_info["uid"]})')
        dashboard = self.grafana.dashboard.get_dashboard(dashboard_info["uid"])
        self.data.dashboards.append(dashboard)
        if self.taqadum is not None:
            self.taqadum.update(1)

    def fetch_dashboards(self):
        log.info("Fetching dashboards one by one")
        results = self.data.dashboard_list
        for dashboard_info in results:
            self.fetch_dashboard(dashboard_info)

    def fetch_dashboards_parallel(self):
        # https://hackernoon.com/how-to-run-asynchronous-web-requests-in-parallel-with-python-3-5-without-aiohttp-264dc0f8546
        loop = asyncio.get_event_loop()
        future = asyncio.ensure_future(self.execute_parallel())
        loop.run_until_complete(future)

    async def execute_parallel(self):
        # https://hackernoon.com/how-to-run-asynchronous-web-requests-in-parallel-with-python-3-5-without-aiohttp-264dc0f8546
        log.info(f"Fetching dashboards in parallel with {self.concurrency} concurrent requests")
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            # Set any session parameters here before calling `fetch`
            loop = asyncio.get_event_loop()
            # START_TIME = default_timer()

            tasks = []
            for dashboard_info in self.data.dashboard_list:
                task = loop.run_in_executor(executor, self.fetch_dashboard, dashboard_info)
                tasks.append(task)

            # Currently, we are not interested in the responses.
            # for response in await asyncio.gather(*tasks):
            #    pass

    @staticmethod
    def get_red_message(message):
        return colored.stylize(message, colored.fg("red") + colored.attr("bold"))


class GrafanaWtf(GrafanaEngine):
    def info(self):
        response = OrderedDict(
            grafana=OrderedDict(
                version=self.version,
                url=self.grafana_url,
            ),
            statistics=OrderedDict(),
            summary=OrderedDict(),
        )

        # Count numbers of first-level entities.
        try:
            self.scan_all()

            response["statistics"] = self.data.admin_stats

            # Compute dashboards without folders.
            dashboards_wo_folders = [db for db in self.data.dashboards if not db.meta.isFolder]

            # Add summary information.
            response["summary"]["annotations"] = len(self.data.annotations)
            response["summary"]["dashboards"] = len(dashboards_wo_folders)
            response["summary"]["datasources"] = len(self.data.datasources)
            response["summary"]["folders"] = len(self.data.folders)
            response["summary"]["notifications"] = len(self.data.notifications)
            response["summary"]["organizations"] = len(self.data.organizations)
            response["summary"]["snapshots"] = len(self.data.snapshots)
            response["summary"]["teams"] = len(self.data.teams)
            response["summary"]["users"] = len(self.data.users)

        except Exception as ex:
            log.error(f"Computing basic statistics failed: {ex}")

        # Count numbers of panels, annotations and variables for all dashboards.
        try:
            dashboard_summary = OrderedDict(
                dashboard_panels=0, dashboard_annotations=0, dashboard_templating=0
            )
            for dbdetails in self.dashboard_details():
                # TODO: Should there any deduplication be applied when counting those entities?
                dashboard_summary["dashboard_panels"] += len(dbdetails.panels)
                dashboard_summary["dashboard_annotations"] += len(dbdetails.annotations)
                dashboard_summary["dashboard_templating"] += len(dbdetails.templating)
            response["summary"].update(dashboard_summary)
        except Exception as ex:
            log.error(f"Computing nested statistics failed: {ex}")

        return response

    @property
    def build_info(self):
        response = None
        error = None
        error_template = (
            f"The request to {self.grafana_url.rstrip('/')}/api/frontend/settings failed"
        )
        try:
            response = self.grafana.client.GET("/frontend/settings")
            if not isinstance(response, dict):
                error = f"{error_template}: Invalid response, content was: {response}"

            response = Munch(response)
            response = response.get("buildInfo")
            if not response:
                error = f"{error_template}: No buildInfo found in the settings response"

        except Exception as ex:
            error = f"{error_template}: {ex}"

        if error:
            log.critical(error)
            raise ConnectionError(error)

        return response

    @property
    def version(self):
        return self.build_info.get("version")

    def dashboard_details(self):
        for dashboard in self.data.dashboards:
            yield DashboardDetails(dashboard=dashboard)

    def search(self, expression):
        log.info(
            'Searching Grafana at "{}" for expression "{}"'.format(self.grafana_url, expression)
        )

        results = Munch(datasources=[], dashboard_list=[], dashboards=[])

        # Check datasources
        log.info("Searching data sources")
        self.search_items(expression, self.data.datasources, results.datasources)

        # Check dashboards
        log.info("Searching dashboards")
        self.search_items(expression, self.data.dashboards, results.dashboards)

        return results

    def replace(self, expression, replacement, dry_run: bool = False):
        if dry_run:
            log.info("Dry-run mode enabled, skipping any actions")
        log.info(
            f'Replacing "{expression}" by "{replacement}" within Grafana at "{self.grafana_url}"'
        )
        for dashboard in self.data.dashboards:
            payload_before = json.dumps(dashboard)
            payload_after = payload_before.replace(expression, replacement)
            if payload_before == payload_after:
                log.info(f'No replacements for dashboard with uid "{dashboard.dashboard.uid}"')
                continue
            dashboard_new = json.loads(payload_after)
            dashboard_new["message"] = f'grafana-wtf: Replaced "{expression}" by "{replacement}"'
            if not dry_run:
                self.grafana.dashboard.update_dashboard(dashboard=dashboard_new)

    def log(self, dashboard_uid=None):
        if dashboard_uid:
            what = 'Grafana dashboard "{}"'.format(dashboard_uid)
        else:
            what = "multiple Grafana dashboards"
        log.info(f"Acquiring data for {what}")

        uid_filter = None
        if dashboard_uid:
            uid_filter = [dashboard_uid]
        dashboards = self.scan_dashboards(dashboard_uids=uid_filter)

        log.info(f"Aggregating edit history for {what}")
        entries = []
        for dashboard in dashboards:
            dashboard_data = dashboard["dashboard"]
            dashboard_meta = dashboard["meta"]

            if dashboard_uid is not None and dashboard_data["uid"] != dashboard_uid:
                continue

            dashboard_versions = self.get_dashboard_versions(dashboard_data["id"])
            for dashboard_revision in dashboard_versions:
                entry = OrderedDict(
                    version=dashboard_revision["version"],
                    datetime=dashboard_revision["created"],
                    user=dashboard_revision["createdBy"],
                    message=dashboard_revision["message"],
                    folder=dashboard_meta.get("folderTitle"),
                    title=dashboard_data["title"],
                    url=urljoin(self.grafana_url, dashboard_meta["url"]),
                    id=dashboard_data["id"],
                    uid=dashboard_data["uid"],
                )
                entries.append(entry)

        return entries

    def search_items(self, expression, items, results):
        for item in items:
            effective_item = None
            if expression is None:
                effective_item = munchify({"meta": {}, "data": item})
            else:
                matches = self.finder.find(expression, item)
                if matches:
                    effective_item = munchify({"meta": {"matches": matches}, "data": item})

            if effective_item:
                results.append(effective_item)

    def get_dashboard_versions(self, dashboard_id):
        # https://grafana.com/docs/http_api/dashboard_versions/
        get_dashboard_versions_path = "/dashboards/id/%s/versions" % dashboard_id
        return self.grafana.dashboard.client.GET(get_dashboard_versions_path)

    def explore_datasources(self):
        # Prepare indexes, mapping dashboards by uid, datasources by name
        # as well as dashboards to datasources and vice versa.
        ix = Indexer(engine=self)

        # Compute list of exploration items, associating
        # datasources with the dashboards that use them.
        results_used = []
        results_unused = []
        for datasource in ix.datasources:
            ds_identifier = datasource.get("uid", datasource.get("name"))
            dashboard_uids = ix.datasource_dashboard_index.get(ds_identifier, [])
            dashboards = list(map(ix.dashboard_by_uid.get, dashboard_uids))
            item = DatasourceExplorationItem(
                datasource=datasource, used_in=dashboards, grafana_url=self.grafana_url
            )

            # Format results in a more compact form, using only a subset of all the attributes.
            result = item.format_compact()

            if dashboard_uids:
                results_used.append(result)
            else:
                if result not in results_unused:
                    results_unused.append(result)

        results_used = sorted(
            results_used, key=lambda x: x["datasource"]["name"] or x["datasource"]["uid"]
        )
        results_unused = sorted(
            results_unused, key=lambda x: x["datasource"]["name"] or x["datasource"]["uid"]
        )

        return OrderedDict(
            used=results_used,
            unused=results_unused,
        )

    def explore_dashboards(self, with_data_details: bool = False, queries_only: bool = False):
        # Prepare indexes, mapping dashboards by uid, datasources by name
        # as well as dashboards to datasources and vice versa.
        ix = Indexer(engine=self)

        # Those dashboard names or uids will be ignored.
        ignore_dashboards = ["-- Grafana --", "-- Mixed --", "grafana", "-- Dashboard --"]

        # Compute list of exploration items, looking
        # for dashboards with missing data sources.
        results = []
        for uid in sorted(ix.dashboard_by_uid):
            dashboard = ix.dashboard_by_uid[uid]
            datasource_items = ix.dashboard_datasource_index[uid]

            datasources_existing = []
            datasources_missing = []
            for datasource_item in datasource_items:
                if (
                    datasource_item.name in ignore_dashboards
                    or datasource_item.uid in ignore_dashboards
                    or datasource_item.type == "grafana"
                ):
                    continue
                datasource_by_uid = ix.datasource_by_uid.get(datasource_item.uid)
                datasource_by_name = ix.datasource_by_name.get(datasource_item.name)
                datasource = datasource_by_uid or datasource_by_name
                if datasource:
                    datasources_existing.append(datasource)
                else:
                    datasources_missing.append(dataclasses.asdict(datasource_item))
            item = DashboardExplorationItem(
                dashboard=dashboard, datasources=datasources_existing, grafana_url=self.grafana_url
            )

            # Format results, using only a subset of all the attributes.
            result = item.format(with_data_details=with_data_details, queries_only=queries_only)
            if result is None:
                continue

            # Add information about missing data sources.
            if datasources_missing:
                result["datasources_missing"] = datasources_missing

            results.append(result)

        return results

    def explore_permissions(self):
        self.scan_folders()
        self.scan_dashboards()

        items = []
        for folder in self.data.folders:
            perms = self.grafana.folder.get_folder_permissions(folder["uid"])
            item = OrderedDict(item=folder, type="folder", permissions=perms)
            items.append(item)

        for dashboard in self.data.dashboards:
            perms = self.grafana.dashboard.get_permissions_by_uid(dashboard["dashboard"]["uid"])
            item = OrderedDict(item=dashboard["meta"], type="dashboard", permissions=perms)
            items.append(item)

        return items

    def plugins_list(self):
        return self.grafana.plugin.list()

    def plugins_status(self):
        status = []
        plugins = self.grafana.plugin.list()
        for plugin in plugins:
            item = self.get_plugin_status(plugin)
            status.append(item)
        return status

    def get_plugin_status(self, plugin):
        plugin = munchify(plugin)
        item = Munch(
            name=plugin.name,
            type=plugin.type,
            id=plugin.id,
            enabled=plugin.enabled,
            category=plugin.category,
            version=plugin.info.version,
            signature=plugin.get("signature"),
        )

        # Status inquiry is not provided by all plugins. Let's filter them.
        # Effectively, run it only on non-internal "app" and "datasource" items.
        if item.type != "panel" and item.signature != "internal":
            try:
                item.health = self.grafana.plugin.health(plugin.id)
            except Exception as ex:
                log.warning(f"Health check failed for plugin {item.id}, type={item.type}: {ex}")
            try:
                item.metrics = self.grafana.plugin.metrics(plugin.id)
            except Exception as ex:
                log.warning(f"Metrics inquiry failed for plugin {item.id}, type={item.type}: {ex}")
        else:
            log.info(f"Skipping status inquiry for plugin {item.id}, type={item.type}")
        return item

    def plugins_list_by_id(self, plugin_id):
        return self.grafana.plugin.by_id(plugin_id=plugin_id)

    def plugins_status_by_id(self, plugin_id):
        plugin = self.plugins_list_by_id(plugin_id)
        return self.get_plugin_status(plugin)

    def channels_list(self):
        return self.grafana.notifications.lookup_channels()

    def channels_list_by_uid(self, channel_uid):
        try:
            channel = self.grafana.notifications.get_channel_by_uid(channel_uid)
        except GrafanaClientError as ex:
            log.error(f"Error fetching the channel {channel_uid}: {ex}")
            raise SystemExit(1) from ex

        # Scan dashboards and panels to find where the channel is used
        dashboards = self.scan_dashboards()
        related_panels = []
        for dashboard in dashboards:
            for panel in dashboard["dashboard"].get("panels", []):
                if "alert" in panel and panel["alert"]["notifications"]:
                    related_panels += self.extract_channel_related_information(
                        channel_uid, dashboard, panel
                    )

                # Some dashboards have a deeper nested structure
                elif "panels" in panel:
                    for subpanel in panel["panels"]:
                        if "alert" in subpanel and subpanel["alert"]["notifications"]:
                            related_panels += self.extract_channel_related_information(
                                channel_uid, dashboard, subpanel
                            )
        if related_panels:
            channel["related_panels"] = related_panels
        return channel

    @staticmethod
    def extract_channel_related_information(channel_uid, dashboard, panel):
        related_information = []
        for notification in panel["alert"]["notifications"]:
            if "uid" in notification and notification["uid"] == channel_uid:
                related_information.append(
                    {"dashboard": dashboard["dashboard"]["title"], "panel": panel["title"]}
                )
        return related_information

    def channels_list_by_name(self, name):
        channel_list = self.channels_list()
        channel_uid = ""
        for channel in channel_list:
            if channel["name"] == name:
                channel_uid = channel["uid"]
                break
        if channel_uid:
            return self.channels_list_by_uid(channel_uid)
        else:
            log.info(f"Channel with the name {name} doesn't exist")
            raise SystemExit(0)


class Indexer:
    def __init__(self, engine: GrafanaWtf):
        self.engine = engine

        # Prepare index data structures.
        self.dashboard_by_uid = {}
        self.datasource_by_ident = {}
        self.datasource_by_uid = {}
        self.datasource_by_name = {}
        self.dashboard_datasource_index = {}
        self.datasource_dashboard_index = {}

        # Gather all data.
        self.dashboards = self.engine.scan_dashboards()
        self.datasources = self.engine.scan_datasources()

        # Invoke indexer.
        self.index()

    def index(self):
        self.index_datasources()
        self.index_dashboards()
        self.index_crossref()

    def collect_datasource_items(self, element):
        element = element or []
        items = []

        def add(item):
            if item is not None and item not in items:
                items.append(item)

        for node in element:
            # Directly defined datasources.
            if "datasource" in node and node["datasource"]:
                ds = node.datasource
                if isinstance(ds, str):
                    add(ds)
                elif isinstance(ds, Munch):
                    ds = dict(ds)
                    add(ds)
                continue

            # Datasources defined as variables.
            if "type" in node and node["type"] == "datasource":
                values = to_list(node.get("current", {}).get("value"))
                for ds_uid in values:
                    datasource = self.datasource_by_uid.get(ds_uid)
                    if datasource is None:
                        log.warning(f"Data source '{ds_uid}' not found")
                        continue
                    ds = dict(
                        type=datasource.get("type"),
                        uid=datasource.get("uid"),
                        name=datasource.get("name"),
                        url=datasource.get("url"),
                    )
                    add(ds)
                continue

        return items

    def index_dashboards(self):
        self.dashboard_by_uid = {}
        self.dashboard_datasource_index = {}

        for dbdetails in self.engine.dashboard_details():
            dashboard = dbdetails.dashboard

            if dashboard.meta.isFolder:
                continue

            # Index by uid.
            uid = dashboard.dashboard.uid
            self.dashboard_by_uid[uid] = dashboard

            # Map to data source names.
            ds_panels = self.collect_datasource_items(dbdetails.panels)
            ds_annotations = self.collect_datasource_items(dbdetails.annotations)
            ds_templating = self.collect_datasource_items(dbdetails.templating)

            results = []
            for bucket in ds_panels, ds_annotations, ds_templating:
                for item in bucket:
                    item = DatasourceItem.from_payload(item)
                    if item not in results:
                        results.append(item)
            self.dashboard_datasource_index[uid] = results

    def index_datasources(self):
        self.datasource_by_ident = {}
        self.datasource_by_uid = {}
        self.datasource_by_name = {}
        self.datasource_dashboard_index = {}

        for datasource in self.datasources:
            self.datasource_by_ident[datasource.name] = datasource
            self.datasource_by_name[datasource.name] = datasource
            if "uid" in datasource:
                self.datasource_by_ident[datasource.uid] = datasource
                self.datasource_by_uid[datasource.uid] = datasource

    def index_crossref(self):
        for dashboard_uid, datasource_items in self.dashboard_datasource_index.items():
            datasource_item: DatasourceItem
            for datasource_item in datasource_items:
                datasource_name_or_uid = datasource_item.uid or datasource_item.name
                if datasource_name_or_uid in self.datasource_by_name:
                    if "uid" in self.datasource_by_name[datasource_name_or_uid]:
                        datasource_name_or_uid = self.datasource_by_name[datasource_name_or_uid].uid
                self.datasource_dashboard_index.setdefault(datasource_name_or_uid, [])
                self.datasource_dashboard_index[datasource_name_or_uid].append(dashboard_uid)
