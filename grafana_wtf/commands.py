# -*- coding: utf-8 -*-
# (c) 2019 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import os
import logging
from docopt import docopt, DocoptExit
from grafana_wtf import __appname__, __version__
from grafana_wtf.core import GrafanaSearch
from grafana_wtf.util import normalize_options, setup_logging

log = logging.getLogger(__name__)


def run():
    """
    Usage:
      grafana-wtf [--grafana-url=<grafana-url>] <expression>
      grafana-wtf --version
      grafana-wtf (-h | --help)

    Options:
      --grafana-url=<grafana-url>   URL to Grafana instance
      --version                     Show version information
      --debug                       Enable debug messages
      -h --help                     Show this screen

    Note:

      Instead of obtaining the URL to the Grafana instance using
      the command line option "--grafana-url", you can use the
      environment variable "GRAFANA_URL". Enjoy.

    Examples:

      # Search through all Grafana entities for string "ldi_readings".
      grafana-wtf --grafana-url=https://daq.example.org/grafana/ ldi_readings

    """

    # Parse command line arguments
    options = normalize_options(docopt(run.__doc__, version=__appname__ + ' ' + __version__))

    # Setup logging
    debug = options.get('debug')
    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG
    setup_logging(log_level)

    # Debugging
    #log.info('Options: {}'.format(json.dumps(options, indent=4)))

    # Sanity checks
    grafana_url = options['grafana-url'] or os.getenv('GRAFANA_URL')
    if grafana_url is None:
        raise DocoptExit('No Grafana URL given. Please use "--grafana-url" option or environment variable "GRAFANA_URL".')

    engine = GrafanaSearch(grafana_url)
    results = engine.search(options['expression'])
    print(results)
