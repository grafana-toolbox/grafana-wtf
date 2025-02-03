# -*- coding: utf-8 -*-
# (c) 2019-2021 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import logging
import textwrap
from collections import OrderedDict
from urllib.parse import urljoin

import colored

from grafana_wtf.util import format_dict, prettify_json

log = logging.getLogger(__name__)


class TextualSearchReport:
    def __init__(self, grafana_url, verbose=False):
        self.grafana_url = grafana_url
        self.verbose = verbose

    def display(self, expression, result):
        expression = expression or "*"
        print(
            'Searching for expression "{}" at Grafana instance {}'.format(
                _m(expression), self.grafana_url
            )
        )
        self.output_items("Data Sources", result.datasources, self.compute_url_datasource)
        self.output_items("Dashboards", result.dashboards, self.compute_url_dashboard)

    def output_items(self, label, items, url_callback):
        # Output section name (data source vs. dashboard).
        hits = len(items)
        print("=" * 42)
        print(f"{_s(label)}: {_m(hits)} hits.")
        print("=" * 42)
        print()

        # Iterate all items having matches.
        for item in items:
            # print('item:', item)

            if self.verbose:
                print()
                print(prettify_json(item.data))

            # Output match title / entity name.
            name = self.get_item_name(item)
            section = f"{_s(label)[:-1]} »{name}«"
            print(_ssb(section))
            print("=" * len(section))

            # Compute some URLs
            url = url_callback(item)
            urls = {
                "Dashboard": _v(url),
                "Variables": _v(url + "?editview=templating"),
            }

            # Output baseline bibliographic data.
            print()
            bibdata_output = self.get_bibdata_dashboard(item, **urls)
            if bibdata_output:
                print(bibdata_output)

            # Separate matches into "dashboard"- and "panels"-groups.
            dashboard_matches = []
            panel_matches = []
            if "matches" in item.meta:
                # print(' ', self.format_where(item))
                for match in item.meta.matches:
                    panel = self.get_panel(match)
                    if panel is not None:
                        panel_matches.append((match, panel))
                    else:
                        dashboard_matches.append(match)

            # Output dashboard matches.
            print()
            subsection = "Global"
            print(_ss(subsection))
            print("-" * len(subsection))
            for match in dashboard_matches:
                match_text = f"- {self.format_match(match)}"
                print(match_text)

            # Output panel bibdata with matches.
            seen = {}
            for match, panel in panel_matches:
                if panel.id not in seen:
                    seen[panel.id] = True
                    print()

                    title = self.get_panel_title(panel)
                    subsection = f"Panel »{title}«"
                    print(_ss(subsection))
                    print("-" * len(subsection))

                    print(self.get_bibdata_panel(panel, url))
                    print("      Matches")

                match_text = f"- {self.format_match(match)}"
                print(textwrap.indent(match_text, " " * 14))

            print()
            print()

    @staticmethod
    def format_match(match):
        return "{path}: {value}".format(
            path=_k(match.full_path), value=_m(str(match.value).strip())
        )

    def get_panel(self, node):
        """
        Find panel from jsonpath node.
        """
        while node:
            last_node = node
            node = node.context
            if node is None:
                break
            if str(node.path) == "panels":
                return last_node.value
        return None

    def get_bibdata_panel(self, panel, baseurl, **kwargs):
        """
        Summarize panel bibliographic data.
        """
        bibdata = OrderedDict()
        bibdata["Id"] = _v(panel.id)
        bibdata["Title"] = _v(self.get_panel_title(panel))
        bibdata["Description"] = _v(str(panel.get("description", "")).strip())
        bibdata["View"] = _v(baseurl + f"?viewPanel={panel.id}")
        bibdata["Edit"] = _v(baseurl + f"?editPanel={panel.id}")
        bibdata.update(kwargs)
        return format_dict(bibdata)

    def get_item_name(self, item):
        if "name" in item.data:
            return item.data.name
        elif "meta" in item.data and "slug" in item.data.meta:
            return item.data.meta.slug
        else:
            return "unknown"

    def get_panel_title(self, panel):
        return panel.get("title", "")

    def get_bibdata_dashboard(self, item, **kwargs):
        """
        Summarize dashboard bibliographic data.
        """

        # Sanity checks.
        if "dashboard" not in item.data:
            return None

        bibdata = OrderedDict()
        bibdata["Title"] = _v(item.data.dashboard.title)
        bibdata["Folder"] = _v(item.data.meta.folderTitle)
        bibdata["UID"] = _v(item.data.dashboard.uid)
        bibdata["Created"] = _v(f"at {item.data.meta.created} by {item.data.meta.createdBy} ")
        bibdata["Updated"] = _v(f"at {item.data.meta.updated} by {item.data.meta.updatedBy}")
        bibdata.update(kwargs)
        return format_dict(bibdata)

    def format_where(self, item):
        keys = item.meta.where
        key_word = "keys"
        if len(keys) <= 1:
            key_word = "key"
        return "Found in {key_word}: {keys}".format(keys=_k(", ".join(keys)), key_word=key_word)

    def compute_url_datasource(self, datasource):
        return urljoin(self.grafana_url, "/datasources/edit/{}".format(datasource.data.id))

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


bold_style = colored.attr("bold")
section_style = colored.fg("cyan") + bold_style
subsection_style = colored.fg("magenta")
key_style = colored.fg("blue") + bold_style
match_style = colored.fg("yellow") + bold_style
value_style = colored.fg("white") + bold_style


def _s(text):
    return colored.stylize(str(text), section_style)


def _ss(text):
    return colored.stylize(str(text), subsection_style)


def _ssb(text):
    return colored.stylize(str(text), subsection_style + bold_style)


def _k(text):
    return colored.stylize(str(text), key_style)


def _m(text):
    return colored.stylize(str(text), match_style)


def _v(text):
    return colored.stylize(str(text), value_style)
