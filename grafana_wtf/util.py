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


def setup_logging(level=logging.INFO):
    log_format = '%(asctime)-15s [%(name)-20s] %(levelname)-7s: %(message)s'
    logging.basicConfig(
        format=log_format,
        stream=sys.stderr,
        level=level)

    # TODO: Control debug logging of HTTP requests through yet another commandline option "--debug-http" or "--debug-requests"
    #requests_log = logging.getLogger('requests')
    #requests_log.setLevel(logging.WARN)


def normalize_options(options):
    normalized = {}
    for key, value in options.items():
        key = key.strip('--<>')
        normalized[key] = value
    return munchify(normalized)


def find_needle(needle, haystack):
    jsonpath_expr = parse('$..*')
    scalars = [str, int, float]
    matches = []
    for node in jsonpath_expr.find(haystack):
        if type(node.value) in scalars:
            value = json.dumps(node.value)
            # TODO: Add regex support.
            if needle in value:
                matches.append(node)
    return matches


def prettify_json(data):
    json_str = json.dumps(data, indent=4)
    return highlight(json_str, JsonLexer(), TerminalFormatter())
