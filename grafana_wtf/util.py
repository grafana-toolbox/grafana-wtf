# -*- coding: utf-8 -*-
# (c) 2019 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import sys
import logging
from munch import munchify


def setup_logging(level=logging.INFO):
    log_format = '%(asctime)-15s [%(name)-30s] %(levelname)-7s: %(message)s'
    logging.basicConfig(
        format=log_format,
        stream=sys.stderr,
        level=level)

    # TODO: Control debug logging of HTTP requests through yet another commandline option "--debug-http" or "--debug-requests"
    requests_log = logging.getLogger('requests')
    requests_log.setLevel(logging.WARN)


def normalize_options(options):
    normalized = {}
    for key, value in options.items():
        key = key.strip('--<>')
        normalized[key] = value
    return munchify(normalized)
