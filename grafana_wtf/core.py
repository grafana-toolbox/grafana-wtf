# -*- coding: utf-8 -*-
# (c) 2019 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import colored
import logging
import requests_cache
from tqdm import tqdm
from munch import Munch, munchify
from urllib.parse import urlparse, urljoin
from collections import OrderedDict

from grafana_api.grafana_api import GrafanaClientError, GrafanaUnauthorizedError
from grafana_api.grafana_face import GrafanaFace
from grafana_wtf.util import JsonPathFinder

log = logging.getLogger(__name__)


class GrafanaSearch:

    def __init__(self, grafana_url, grafana_token):
        self.grafana_url = grafana_url
        self.grafana_token = grafana_token

        self.grafana = None
        self.data = Munch(datasources=[], dashboard_list=[], dashboards=[])

        self.finder = JsonPathFinder()

    def enable_cache(self, expire_after=300, drop_cache=False):
        if expire_after is None:
            log.info(f'Setting up response cache to never expire (infinite caching)')
        else:
            log.info(f'Setting up response cache to expire after {expire_after} seconds')
        requests_cache.install_cache(expire_after=expire_after)
        if drop_cache:
            log.info(f'Dropping cache')
            requests_cache.clear()

        return self

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
            host=url.hostname, port=url.port, url_path_prefix=url.path)

        return self

    def search(self, expression):
        log.info('Searching Grafana at "{}" for expression "{}"'.format(self.grafana_url, expression))
        self.scan()

        results = Munch(datasources=[], dashboard_list=[], dashboards=[])

        # Check datasources
        log.info('Searching data sources')
        self.search_items(expression, self.data.datasources, results.datasources)

        # Check dashboards
        log.info('Searching dashboards')
        self.search_items(expression, self.data.dashboards, results.dashboards)

        return results

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
            self.data.datasources = self.grafana.datasource.list_datasources()
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

    def scan_dashboards(self):

        log.info('Scanning dashboards')
        try:
            self.data.dashboard_list = self.grafana.search.search_dashboards()
            log.info('Found {} dashboards'.format(len(self.data.dashboard_list)))
        except GrafanaClientError as ex:
            message = '{name}: {ex}'.format(name=ex.__class__.__name__, ex=ex)
            message = colored.stylize(message, colored.fg("red") + colored.attr("bold"))
            log.error(self.get_red_message(message))
            if isinstance(ex, GrafanaUnauthorizedError):
                log.error(self.get_red_message('Please use --grafana-token or GRAFANA_TOKEN '
                                               'for authenticating with Grafana'))

        log.info('Fetching dashboards')
        for dashboard_info in tqdm(self.data.dashboard_list):
            dashboard = self.grafana.dashboard.get_dashboard(dashboard_info['uid'])
            self.data.dashboards.append(dashboard)

    def get_dashboard_versions(self, dashboard_id):
        """

        :param dashboard_id:
        :return:
        """
        # https://grafana.com/docs/http_api/dashboard_versions/
        get_dashboard_versions_path = '/dashboards/id/%s/versions' % dashboard_id
        r = self.grafana.dashboard.api.GET(get_dashboard_versions_path)
        return r
