# -*- coding: utf-8 -*-
# (c) 2019 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import sys
import json
import logging
from munch import munchify
from jsonpath_rw import parse
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import TerminalFormatter

log = logging.getLogger(__name__)


def setup_logging(level=logging.INFO):
    log_format = '%(asctime)-15s [%(name)-22s] %(levelname)-7s: %(message)s'
    logging.basicConfig(
        format=log_format,
        stream=sys.stderr,
        level=level)

    # Todo: Control debug logging of HTTP requests through yet another commandline option "--debug-http" or "--debug-requests"
    #requests_log = logging.getLogger('requests')
    #requests_log.setLevel(logging.INFO)

    requests_log = logging.getLogger('urllib3.connectionpool')
    requests_log.setLevel(logging.INFO)


def normalize_options(options):
    normalized = {}
    for key, value in options.items():
        key = key.strip('--<>')
        normalized[key] = value
    return munchify(normalized)


class JsonPathFinder:

    def __init__(self):
        self.jsonpath_expr = parse('$..*')
        self.non_leaf_nodes = ('rows', 'panels', 'targets', 'tags', 'groupBy', 'list', 'links')
        self.scalars = (str, int, float, list)

    def find(self, needle, haystack):
        matches = []

        # Iterate JSON, node by node.
        for node in self.jsonpath_expr.find(haystack):

            # Ignore empty nodes.
            if node.value is None:
                continue

            # Ignore top level nodes.
            if str(node.path) in self.non_leaf_nodes:
                continue

            if isinstance(node.value, self.scalars):

                # Check if node matches search expression. Currently, this
                # is essentially a basic "string contains" match but it might
                # be improved in the future.
                # Todo: Use regex or other more sophisticated search expressions.
                if needle in str(node.value):
                    matches.append(node)

            else:
                if not isinstance(node.value, dict):
                    log.warning(f'Ignored data type {type(node.value)} when matching.\n'
                                f'Node was "{node.path}", value was "{node.value}".')

        return matches


def prettify_json(data):
    json_str = json.dumps(data, indent=4)
    return highlight(json_str, JsonLexer(), TerminalFormatter())
