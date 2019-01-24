# -*- coding: utf-8 -*-
# (c) 2019 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import os
import logging
from docopt import docopt, DocoptExit
from grafana_wtf import __appname__, __version__
from grafana_wtf.core import GrafanaSearch
from grafana_wtf.report import WtfReport
from grafana_wtf.util import normalize_options, setup_logging

log = logging.getLogger(__name__)


def run():
    """
    Usage:
      grafana-wtf [--grafana-url=<grafana-url>] [--verbose] find [<expression>]
      grafana-wtf --version
      grafana-wtf (-h | --help)

    Options:
      --grafana-url=<grafana-url>   URL to Grafana instance
      --verbose                     Enable verbose mode
      --version                     Show version information
      --debug                       Enable debug messages
      -h --help                     Show this screen

    Note:

      Instead of obtaining the URL to the Grafana instance using
      the command line option "--grafana-url", you can use the
      environment variable "GRAFANA_URL". Enjoy.

    Examples:

      # Search through all Grafana entities for string "ldi_readings".
      grafana-wtf --grafana-url=https://admin:admin@daq.example.org/grafana/ find ldi_readings

      # Search Grafana instance for string "luftdaten", using more convenient invoking flavor.
      export GRAFANA_URL=https://admin:admin@daq.example.org/grafana/
      grafana-wtf find luftdaten

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
    expression = options['expression']
    if options.find:
        result = engine.search(expression)
        #print(json.dumps(result, indent=4))

        report = WtfReport(grafana_url, verbose=options.verbose)
        report.display(expression, result)
