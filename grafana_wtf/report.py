# -*- coding: utf-8 -*-
# (c) 2019 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import colored
import logging
from six import StringIO
from urllib.parse import urljoin
from collections import OrderedDict
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

            if self.verbose:
                print()
                print(prettify_json(item.data))

            # Output match title / entity name.
            name = self.get_item_name(item)
            print(_v(name))
            print('-' * len(name))

            # Output URL
            url = url_callback(item)

            # Output baseline bibliographic data.
            print()
            bibdata_output = self.get_bibdata(item, URL=_vlow(url))
            if bibdata_output:
                print(bibdata_output)

            # Output findings.
            if 'matches' in item.meta:
                #print(' ', self.format_where(item))
                for match in item.meta.matches:
                    print('- {path}: {value}'.format(path=_k(match.full_path), value=_v(match.value)))

            print()
            print()

    def get_item_name(self, item):
        if 'name' in item.data:
            return item.data.name
        elif 'meta' in item.data and 'slug' in item.data.meta:
            return item.data.meta.slug
        else:
            return 'unknown'

    def get_bibdata(self, item, **kwargs):

        # Sanity checks.
        if 'dashboard' not in item.data:
            return

        bibdata = OrderedDict()
        bibdata['Title'] = item.data.dashboard.title
        bibdata['Folder'] = item.data.meta.folderTitle
        bibdata['UID'] = item.data.dashboard.uid
        bibdata['Created'] = f'at {item.data.meta.created} by {item.data.meta.createdBy} '
        bibdata['Updated'] = f'at {item.data.meta.updated} by {item.data.meta.updatedBy}'
        bibdata.update(kwargs)
        output = StringIO()
        for key, value in bibdata.items():
            entry = f' {key:>7} {value}\n'
            output.write(entry)
        output.seek(0)
        return output.read()

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

    def experimental(self):
        # print(match)
        # print(dir(match.context))
        # print(match.context)
        # pprint(match.context.value)
        # idp = parse('id')
        # if match.context.parse('id'):
        #    print('  id:', match.context.id)
        # pprint(match)
        pass

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
