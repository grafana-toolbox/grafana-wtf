# -*- coding: utf-8 -*-
# (c) 2019 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import json
import colored
import logging
import asyncio
import requests
import requests_cache
from tqdm import tqdm
from munch import Munch, munchify
from collections import OrderedDict
from urllib.parse import urlparse, urljoin
from concurrent.futures.thread import ThreadPoolExecutor

from grafana_wtf.model import DatasourceExplorationItem, DashboardExplorationItem, GrafanaDataModel
from grafana_wtf.monkey import monkeypatch_grafana_api
# Apply monkeypatch to grafana-api
# https://github.com/m0nhawk/grafana_api/pull/85/files
monkeypatch_grafana_api()

from grafana_api.grafana_api import GrafanaClientError, GrafanaUnauthorizedError
from grafana_api.grafana_face import GrafanaFace

from grafana_wtf.util import JsonPathFinder

log = logging.getLogger(__name__)


class GrafanaEngine:

    def __init__(self, grafana_url, grafana_token):
        self.grafana_url = grafana_url
        self.grafana_token = grafana_token

        self.grafana = None
        self.data = GrafanaDataModel()

        self.finder = JsonPathFinder()

        self.taqadum = None
        self.concurrency = 5

        self.debug = log.getEffectiveLevel() == logging.DEBUG
        self.progressbar = not self.debug

    def enable_cache(self, expire_after=300, drop_cache=False):
        if expire_after is None:
            log.info(f'Setting up response cache to never expire (infinite caching)')
        else:
            log.info(f'Setting up response cache to expire after {expire_after} seconds')
        requests_cache.install_cache(expire_after=expire_after)
        if drop_cache:
            self.clear_cache()

        return self

    def clear_cache(self):
        log.info(f'Clearing cache')
        requests_cache.clear()

    def enable_concurrency(self, concurrency):
        self.concurrency = concurrency

    @staticmethod
    def grafana_client_factory(grafana_url, grafana_token=None):
        url = urlparse(grafana_url)

        # Grafana API Key auth
        if grafana_token:
            auth = grafana_token

        # HTTP basic auth
        else:
            username = url.username or 'admin'
            password = url.password or 'admin'
            auth = (username, password)

        grafana = GrafanaFace(
            auth, protocol=url.scheme,
            host=url.hostname, port=url.port, url_path_prefix=url.path.lstrip('/'))

        return grafana

    def setup(self):

        self.grafana = self.grafana_client_factory(self.grafana_url, grafana_token=self.grafana_token)

        # Configure a larger HTTP request pool.
        # Todo: Review the pool settings and eventually adjust according to concurrency level or other parameters.
        # https://urllib3.readthedocs.io/en/latest/advanced-usage.html#customizing-pool-behavior
        # https://laike9m.com/blog/requests-secret-pool_connections-and-pool_maxsize,89/
        adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=5, pool_block=True)
        self.grafana.api.s.mount('http://', adapter)
        self.grafana.api.s.mount('https://', adapter)

        return self

    def start_progressbar(self, total):
        if self.progressbar:
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
        self.data.notifications = self.grafana.notifications.lookup_channels()

    def scan_datasources(self):
        log.info('Scanning datasources')
        try:
            self.data.datasources = munchify(self.grafana.datasource.list_datasources())
            log.info('Found {} data sources'.format(len(self.data.datasources)))
            return self.data.datasources
        except GrafanaClientError as ex:
            message = '{name}: {ex}'.format(name=ex.__class__.__name__, ex=ex)
            log.error(self.get_red_message(message))
            if isinstance(ex, GrafanaUnauthorizedError):
                log.error(self.get_red_message('Please use --grafana-token or GRAFANA_TOKEN '
                                               'for authenticating with Grafana'))

    def scan_dashboards(self, dashboard_uids=None):

        log.info('Scanning dashboards')
        try:
            if dashboard_uids is not None:
                for uid in dashboard_uids:
                    log.info(f'Fetching dashboard by uid {uid}')
                    try:
                        dashboard = self.grafana.dashboard.get_dashboard(uid)
                        self.data.dashboard_list.append(dashboard['dashboard'])
                    except GrafanaClientError as ex:
                        self.handle_grafana_error(ex)
                        continue
            else:
                self.data.dashboard_list = self.grafana.search.search_dashboards(limit=5000)
            log.info('Found {} dashboards'.format(len(self.data.dashboard_list)))

        except GrafanaClientError as ex:
            self.handle_grafana_error(ex)
            return

        if self.progressbar:
            self.start_progressbar(len(self.data.dashboard_list))

        if self.concurrency is None or self.concurrency <= 1:
            self.fetch_dashboards()
        else:
            self.fetch_dashboards_parallel()

        if self.progressbar:
            self.taqadum.close()

        return self.data.dashboards

    def handle_grafana_error(self, ex):
        message = '{name}: {ex}'.format(name=ex.__class__.__name__, ex=ex)
        message = colored.stylize(message, colored.fg("red") + colored.attr("bold"))
        log.error(self.get_red_message(message))
        if isinstance(ex, GrafanaUnauthorizedError):
            log.error(self.get_red_message('Please use --grafana-token or GRAFANA_TOKEN '
                                           'for authenticating with Grafana'))

    def fetch_dashboard(self, dashboard_info):
        log.debug(f'Fetching dashboard "{dashboard_info["title"]}" ({dashboard_info["uid"]})')
        dashboard = self.grafana.dashboard.get_dashboard(dashboard_info['uid'])
        self.data.dashboards.append(munchify(dashboard))
        if self.taqadum is not None:
            self.taqadum.update(1)

    def fetch_dashboards(self):
        log.info('Fetching dashboards one by one')
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
        log.info(f'Fetching dashboards in parallel with {self.concurrency} concurrent requests')
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:

            # Set any session parameters here before calling `fetch`
            loop = asyncio.get_event_loop()
            # START_TIME = default_timer()

            tasks = []
            for dashboard_info in self.data.dashboard_list:
                task = loop.run_in_executor(
                    executor,
                    self.fetch_dashboard,
                    dashboard_info
                )
                tasks.append(task)

            # Currently, we are not interested in the responses.
            #for response in await asyncio.gather(*tasks):
            #    pass


class GrafanaWtf(GrafanaEngine):

    def info(self):

        try:
            health = self.grafana.api.GET("/health")
        except Exception as ex:
            log.error(f"Request to /health endpoint failed: {ex}")
            health = {}

        response = OrderedDict(
            grafana=OrderedDict(
                version=health.get("version"),
                url=self.grafana_url,
            ),
            statistics=OrderedDict(),
            summary=OrderedDict(),
        )

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
            log.error(f"Scanning resources failed: {ex}")

        return response

    def search(self, expression):
        log.info('Searching Grafana at "{}" for expression "{}"'.format(self.grafana_url, expression))

        results = Munch(datasources=[], dashboard_list=[], dashboards=[])

        # Check datasources
        log.info('Searching data sources')
        self.search_items(expression, self.data.datasources, results.datasources)

        # Check dashboards
        log.info('Searching dashboards')
        self.search_items(expression, self.data.dashboards, results.dashboards)

        return results

    def replace(self, expression, replacement):
        log.info(f'Replacing "{expression}" by "{replacement}" within Grafana at "{self.grafana_url}"')
        for dashboard in self.data.dashboards:
            payload_before = json.dumps(dashboard)
            payload_after = payload_before.replace(expression, replacement)
            if payload_before == payload_after:
                log.info(f'No replacements for dashboard with uid "{dashboard.dashboard.uid}"')
                continue
            dashboard_new = json.loads(payload_after)
            dashboard_new['message'] = f'grafana-wtf: Replaced "{expression}" by "{replacement}"'
            self.grafana.dashboard.update_dashboard(dashboard=dashboard_new)

    def log(self, dashboard_uid=None):
        if dashboard_uid:
            what = 'Grafana dashboard "{}"'.format(dashboard_uid)
        else:
            what = 'multiple Grafana dashboards'
        log.info('Aggregating edit history for {what} at {url}'.format(what=what, url=self.grafana_url))

        entries = []
        for dashboard_meta in self.data.dashboard_list:
            if dashboard_uid is not None and dashboard_meta['uid'] != dashboard_uid:
                continue

            #print(dashboard_meta)

            dashboard_versions = self.get_dashboard_versions(dashboard_meta['id'])
            for dashboard_revision in dashboard_versions:
                entry = OrderedDict(
                    datetime=dashboard_revision['created'],
                    user=dashboard_revision['createdBy'],
                    message=dashboard_revision['message'],
                    folder=dashboard_meta.get('folderTitle'),
                    title=dashboard_meta['title'],
                    version=dashboard_revision['version'],
                    url=urljoin(self.grafana_url, dashboard_meta['url'])
                )
                entries.append(entry)

        return entries

    def search_items(self, expression, items, results):
        for item in items:
            effective_item = None
            if expression is None:
                effective_item = munchify({'meta': {}, 'data': item})
            else:
                matches = self.finder.find(expression, item)
                if matches:
                    effective_item = munchify({'meta': {'matches': matches}, 'data': item})

            if effective_item:
                results.append(effective_item)

    @staticmethod
    def get_red_message(message):
        return colored.stylize(message, colored.fg("red") + colored.attr("bold"))

    def get_dashboard_versions(self, dashboard_id):
        # https://grafana.com/docs/http_api/dashboard_versions/
        get_dashboard_versions_path = '/dashboards/id/%s/versions' % dashboard_id
        r = self.grafana.dashboard.api.GET(get_dashboard_versions_path)
        return r

    def explore_datasources(self):

        # Prepare indexes, mapping dashboards by uid, datasources by name
        # as well as dashboards to datasources and vice versa.
        ix = Indexer(engine=self)

        # Compute list of exploration items, associating datasources with the dashboards that use them.
        results_used = []
        results_unused = []
        for name in sorted(ix.datasource_by_name):
            datasource = ix.datasource_by_name[name]
            dashboard_uids = ix.datasource_dashboard_index.get(name, [])
            dashboards = list(map(ix.dashboard_by_uid.get, dashboard_uids))
            item = DatasourceExplorationItem(datasource=datasource, used_in=dashboards, grafana_url=self.grafana_url)

            # Format results in a more compact form, using only a subset of all the attributes.
            result = item.format_compact()

            if dashboard_uids:
                results_used.append(result)
            else:
                results_unused.append(result)

        response = OrderedDict(
            used=results_used,
            unused=results_unused,
        )

        return response

    def explore_dashboards(self):

        # Prepare indexes, mapping dashboards by uid, datasources by name
        # as well as dashboards to datasources and vice versa.
        ix = Indexer(engine=self)

        # Compute list of exploration items, looking for dashboards with missing data sources.
        results = []
        for uid in sorted(ix.dashboard_by_uid):

            dashboard = ix.dashboard_by_uid[uid]
            datasource_names = ix.dashboard_datasource_index[uid]

            datasources_existing = []
            datasource_names_missing = []
            for datasource_name in datasource_names:
                if datasource_name == "-- Grafana --":
                    continue
                datasource = ix.datasource_by_name.get(datasource_name)
                if datasource:
                    datasources_existing.append(datasource)
                else:
                    datasource_names_missing.append({"name": datasource_name})
            item = DashboardExplorationItem(dashboard=dashboard, datasources=datasources_existing, grafana_url=self.grafana_url)

            # Format results in a more compact form, using only a subset of all the attributes.
            result = item.format_compact()

            # Add information about missing data sources.
            if datasource_names_missing:
                result["datasources_missing"] = datasource_names_missing

            results.append(result)

        return results


class Indexer:

    def __init__(self, engine: GrafanaWtf):
        self.engine = engine

        # Prepare index data structures.
        self.dashboard_by_uid = {}
        self.datasource_by_name = {}
        self.dashboard_datasource_index = {}
        self.datasource_dashboard_index = {}

        # Gather all data.
        self.dashboards = self.engine.scan_dashboards()
        self.datasources = self.engine.scan_datasources()

        # Invoke indexer.
        self.index()

    def index(self):
        self.index_dashboards()
        self.index_datasources()

    @staticmethod
    def collect_datasource_names(element):
        names = []
        for node in element:
            if "datasource" in node and node["datasource"]:
                names.append(node.datasource)
        return list(sorted(set(names)))

    def index_dashboards(self):

        self.dashboard_by_uid = {}
        self.dashboard_datasource_index = {}

        for dashboard in self.dashboards:
            if dashboard.meta.isFolder:
                continue

            # Index by uid.
            uid = dashboard.dashboard.uid
            self.dashboard_by_uid[uid] = dashboard

            # Map to data source names.
            dbdata = dashboard.dashboard
            ds_panels = self.collect_datasource_names(dbdata.get("panels", []))
            ds_annotations = self.collect_datasource_names(dbdata.get("annotations", {}).get("list", []))
            ds_templating = self.collect_datasource_names(dbdata.get("templating", {}).get("list", []))
            self.dashboard_datasource_index[uid] = list(sorted(set(ds_panels + ds_annotations + ds_templating)))

    def index_datasources(self):

        self.datasource_by_name = {}
        self.datasource_dashboard_index = {}

        for datasource in self.datasources:
            name = datasource.name
            self.datasource_by_name[name] = datasource

        for dashboard_uid, datasource_names in self.dashboard_datasource_index.items():
            for datasource_name in datasource_names:
                self.datasource_dashboard_index.setdefault(datasource_name, [])
                self.datasource_dashboard_index[datasource_name].append(dashboard_uid)
