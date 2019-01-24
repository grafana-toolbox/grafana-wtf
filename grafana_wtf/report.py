# -*- coding: utf-8 -*-
# (c) 2019 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import logging
import colored
from urllib.parse import urljoin
from grafana_wtf.util import prettify_json

log = logging.getLogger(__name__)


class WtfReport:

    def __init__(self, grafana_url, verbose=False):
        self.grafana_url = grafana_url
        self.verbose = verbose

    def display(self, expression, result):
        expression = expression or '*'
        print('Searching for expression "{}" at Grafana instance {}'.format(_v(expression), self.grafana_url))
        self.output_items(_s('Data Sources'), result.datasources, self.compute_url_datasource)
        self.output_items(_s('Dashboards'), result.dashboards, self.compute_url_dashboard)

    def output_items(self, label, items, url_callback):

        # Output section name (data source vs. dashboard).
        print('=' * 42)
        print('{label}: {hits} hits.'.format(hits=_v(len(items)), label=label))
        print('=' * 42)
        print()

        # Iterate all items having matches.
        for item in items:
            #print('item:', item)

            # Output match title / entity name.
            name = self.get_item_name(item)
            print(_v(name))
            print('-' * len(name))

            print(_vlow(url_callback(item)))
            if 'matches' in item.meta:
                #print(' ', self.format_where(item))
                print()
                for match in item.meta.matches:
                    print('- {path}: {value}'.format(path=_k(match.full_path), value=_v(match.value)))
            if self.verbose:
                print()
                print(prettify_json(item.data))
            else:
                print()

    def get_item_name(self, item):
        if 'name' in item.data:
            return item.data.name
        elif 'meta' in item.data and 'slug' in item.data.meta:
            return item.data.meta.slug
        else:
            return 'unknown'

    def format_where(self, item):
        keys = item.meta.where
        key_word = 'keys'
        if len(keys) <= 1:
            key_word = 'key'
        answer = 'Found in {key_word}: {keys}'.format(keys=_k(', '.join(keys)), key_word=key_word)
        return answer

    def compute_url_datasource(self, datasource):
        return urljoin(self.grafana_url, '/datasources/edit/{}'.format(datasource.data.id))

    def compute_url_dashboard(self, dashboard):
        return urljoin(self.grafana_url, dashboard.data.meta.url)


section_style = colored.fg("cyan") + colored.attr("bold")
key_style = colored.fg("blue") + colored.attr("bold")
value_style = colored.fg("yellow") + colored.attr("bold")

def _s(text):
    return colored.stylize(str(text), section_style)
def _k(text):
    return colored.stylize(str(text), key_style)
def _v(text):
    return colored.stylize(str(text), value_style)
def _vlow(text):
    return colored.stylize(str(text), colored.fg("white") + colored.attr("bold"))
