# -*- coding: utf-8 -*-
# (c) 2019 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import os
import json
import logging
from tabulate import tabulate
from operator import itemgetter
from collections import OrderedDict
from docopt import docopt, DocoptExit

from grafana_wtf import __appname__, __version__
from grafana_wtf.core import GrafanaSearch
from grafana_wtf.report import WtfReport
from grafana_wtf.util import normalize_options, setup_logging

log = logging.getLogger(__name__)


def run():
    """
    Usage:
      grafana-wtf [options] find [<expression>]
      grafana-wtf [options] log [<dashboard_uid>] [--number=<count>]
      grafana-wtf --version
      grafana-wtf (-h | --help)

    Options:
      --grafana-url=<grafana-url>       URL to Grafana instance
      --grafana-token=<grafana-token>   Grafana API Key token
      --format=<format>                 Output format. [default: json]
      --cache-ttl=<cache-ttl>           Time-to-live for the request cache in seconds. [default: 300]
      --drop-cache                      Drop cache before requesting resources
      --verbose                         Enable verbose mode
      --version                         Show version information
      --debug                           Enable debug messages
      -h --help                         Show this screen

    Note:

      Instead of obtaining the URL to the Grafana instance using
      the command line option "--grafana-url", you can use the
      environment variable "GRAFANA_URL".
      Likewise, use "GRAFANA_TOKEN" instead of "--grafana-token"
      for propagating the Grafana API Key.

    Search examples:

      # Search through all Grafana entities for string "ldi_readings".
      grafana-wtf --grafana-url=https://daq.example.org/grafana/ --grafana-token=eyJrIjoiWHg...dGJpZCI6MX0= find ldi_readings

      # Search Grafana instance for string "luftdaten", using more convenient invoking flavor.
      export GRAFANA_URL=https://daq.example.org/grafana/
      export GRAFANA_TOKEN=eyJrIjoiWHg...dGJpZCI6MX0=
      grafana-wtf find luftdaten

      # Use infinite cache expiration time, essentially caching forever.
      grafana-wtf find '#299c46' --cache-ttl=inf

      # Set cache expiration time to zero, essentially disabling the cache.
      grafana-wtf find geohash --cache-ttl=0

    History examples:

      # Display 50 most recent changes across all dashboards.
      grafana-wtf log --number=50

      # Display 5 most recent changes for specific dashboard.
      grafana-wtf log NP0wTOtmk --number=5

      # Output full history table in Markdown format
      grafana-wtf log --format=tabular:pipe

      # Output full history table in Grid format
      grafana-wtf log --format=tabular:grid


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

    grafana_url = options['grafana-url'] or os.getenv('GRAFANA_URL')
    grafana_token = options['grafana-token'] or os.getenv('GRAFANA_TOKEN')

    # Compute cache expiration time.
    try:
        cache_ttl = int(options['cache-ttl'])
    except:
        if not options['cache-ttl'] or 'infinite'.startswith(options['cache-ttl'].lower()):
            cache_ttl = None
        else:
            raise

    # Sanity checks
    if grafana_url is None:
        raise DocoptExit('No Grafana URL given. Please use "--grafana-url" option or environment variable "GRAFANA_URL".')

    engine = GrafanaSearch(grafana_url, grafana_token)
    engine.enable_cache(expire_after=cache_ttl, drop_cache=options['drop-cache'])
    engine.setup()

    if options.find:
        result = engine.search(options.expression)
        #print(json.dumps(result, indent=4))

        report = WtfReport(grafana_url, verbose=options.verbose)
        report.display(options.expression, result)

    elif options.log:
        engine.scan_dashboards()
        #print(options.dashboard_uid)
        entries = engine.log(dashboard_uid=options.dashboard_uid)
        entries = sorted(entries, key=itemgetter('datetime'), reverse=True)

        if options.number is not None:
            count = int(options.number)
            entries = entries[:count]

        # https://bitbucket.org/astanin/python-tabulate
        output_format = options['format']
        if output_format.startswith('tabular'):

            entries = compact_table(to_table(entries), output_format)

            try:
                tablefmt = options['format'].split(':')[1]
            except:
                tablefmt = 'psql'

            #output = tabulate(data, headers=data.columns, showindex=showindex, tablefmt=tablefmt).encode('utf-8')
            output = tabulate(entries, headers="keys", tablefmt=tablefmt) #.encode('utf-8')

        else:
            output = json.dumps(entries, indent=4)

        print(output)


def to_table(entries):
    for entry in entries:
        item = entry
        name = item['title']
        if item['folder']:
            name = item['folder'].strip() + ' » ' + name.strip()
        item['name'] = name.strip(' 🤓')
        #del item['url']
        del item['folder']
        del item['title']
        del item['version']
        yield item


def compact_table(entries, format):
    seperator = '\n'
    if format.endswith('pipe'):
        seperator = '<br/>'
    for entry in entries:
        item = OrderedDict()
        if format.endswith('pipe'):
            link = '[{}]({})'.format(entry['name'], entry['url'])
        else:
            link = 'Name: {}\nURL: {}'.format(entry['name'], entry['url'])
        item['Dashboard'] = seperator.join([
            'Notes: {}'.format(entry['message'].capitalize() or 'n/a'),
            link,
        ])
        item['Update'] = seperator.join([
            'User: {}'.format(entry['user']),
            'Date: {}'.format(entry['datetime']),
        ])
        yield item
