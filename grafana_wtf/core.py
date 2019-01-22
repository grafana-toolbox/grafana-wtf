# -*- coding: utf-8 -*-
# (c) 2019 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import logging

log = logging.getLogger(__name__)


class GrafanaSearch:

    def __init__(self, grafana_url):
        self.grafana_url = grafana_url

    def search(self, expression):
        log.info('Searching Grafana at "{}" for expression "{}"'.format(self.grafana_url, expression))
