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

from grafana_wtf.monkey import monkeypatch_grafana_api
# Apply monkeypatch to grafana-api
# https://github.com/m0nhawk/grafana_api/pull/85/files
monkeypatch_grafana_api()

from grafana_api.grafana_api import GrafanaClientError, GrafanaUnauthorizedError
from grafana_api.grafana_face import GrafanaFace

from grafana_wtf.util import JsonPathFinder

log = logging.getLogger(__name__)

# Use ANSI colors only on TTYs.
colored.set_tty_aware()


class GrafanaSearch:

    def __init__(self, grafana_url, grafana_token):
        self.grafana_url = grafana_url
        self.grafana_token = grafana_token

        self.grafana = None
        self.data = Munch(datasources=[], dashboard_list=[], dashboards=[])

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

    def setup(self):
        url = urlparse(self.grafana_url)

        # Grafana API Key auth
        if self.grafana_token:
            auth = self.grafana_token

        # HTTP basic auth
        else:
            username = url.username or 'admin'
            password = url.password or 'admin'
            auth = (username, password)

        self.grafana = GrafanaFace(
            auth, protocol=url.scheme,
            host=url.hostname, port=url.port, url_path_prefix=url.path.lstrip('/'))

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

    def scan(self):

        # TODO: Folders?
        # folders = self.grafana.folder.get_all_folders()
        # print(folders)

        self.scan_datasources()
        self.scan_dashboards()

    def scan_datasources(self):
        log.info('Scanning datasources')
        try:
            self.data.datasources = munchify(self.grafana.datasource.list_datasources())
            log.info('Found {} data sources'.format(len(self.data.datasources)))
        except GrafanaClientError as ex:
            message = '{name}: {ex}'.format(name=ex.__class__.__name__, ex=ex)
            log.error(self.get_red_message(message))
            if isinstance(ex, GrafanaUnauthorizedError):
                log.error(self.get_red_message('Please use --grafana-token or GRAFANA_TOKEN '
                                               'for authenticating with Grafana'))

    @staticmethod
    def get_red_message(message):
        return colored.stylize(message, colored.fg("red") + colored.attr("bold"))

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

    def get_dashboard_versions(self, dashboard_id):
        # https://grafana.com/docs/http_api/dashboard_versions/
        get_dashboard_versions_path = '/dashboards/id/%s/versions' % dashboard_id
        r = self.grafana.dashboard.api.GET(get_dashboard_versions_path)
        return r
