# -*- coding: utf-8 -*-
# (c) 2019 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import os
import json
import logging
from functools import partial
from tabulate import tabulate
from operator import itemgetter
from collections import OrderedDict
from docopt import docopt, DocoptExit

from grafana_wtf import __appname__, __version__
from grafana_wtf.core import GrafanaSearch
from grafana_wtf.report import WtfReport
from grafana_wtf.tabular_report import TabularReport
from grafana_wtf.util import normalize_options, setup_logging, configure_http_logging, read_list

log = logging.getLogger(__name__)


def run():
    """
    Usage:
      grafana-wtf [options] find [<search-expression>]
      grafana-wtf [options] replace <search-expression> <replacement>
      grafana-wtf [options] log [<dashboard_uid>] [--number=<count>]
      grafana-wtf --version
      grafana-wtf (-h | --help)

    Options:
      --grafana-url=<grafana-url>       URL to Grafana instance
      --grafana-token=<grafana-token>   Grafana API Key token
      --select-dashboard=<uuid>         Restrict operation to dashboard by UID.
                                        Can be a list of comma-separated dashboard UIDs.
      --format=<format>                 Output format. [default: json]
      --cache-ttl=<cache-ttl>           Time-to-live for the request cache in seconds. [default: 300]
      --drop-cache                      Drop cache before requesting resources
      --concurrency=<concurrency>       Run multiple requests in parallel. [default: 5]
      --verbose                         Enable verbose mode
      --version                         Show version information
      --debug                           Enable debug messages
      --http-logging                    Enable logging for underlying HTTP client machinery
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

      # Search keyword within list of specific dashboards.
      grafana-wtf --select-dashboard=_JJ22OZZk,5iGTqNWZk find grafana-worldmap

      # Output search results in tabular format.
      grafana-wtf find luftdaten --format=tabular:psql

    Replace examples:

      # Replace string within specific dashboard.
      grafana-wtf --select-dashboard=_JJ22OZZk replace grafana-worldmap-panel grafana-map-panel

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
    log.debug('Options: {}'.format(json.dumps(options, indent=4)))

    configure_http_logging(options)

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
    engine.enable_concurrency(int(options['concurrency']))
    engine.setup()

    if options.replace:
        engine.clear_cache()

    output_format = options["format"]

    if options.find or options.replace:

        if options.select_dashboard:
            # Restrict scan to list of dashboards.
            dashboard_uids = read_list(options.select_dashboard)
            engine.scan_dashboards(dashboard_uids)

        else:
            # Scan everything.
            engine.scan()

        result = engine.search(options.search_expression or None)

        if output_format.startswith("tabular"):
            table_format = get_table_format(output_format)
            generator = partial(TabularReport, tblfmt=table_format)
        else:
            generator = WtfReport

        report = generator(grafana_url, verbose=options.verbose)
        report.display(options.search_expression, result)

    if options.replace:
        engine.replace(options.search_expression, options.replacement)
        engine.clear_cache()

    if options.log:
        engine.scan_dashboards()
        entries = engine.log(dashboard_uid=options.dashboard_uid)
        entries = sorted(entries, key=itemgetter('datetime'), reverse=True)

        if options.number is not None:
            count = int(options.number)
            entries = entries[:count]

        # TODO: Refactor tabular formatting to WtfTabularReport class.
        # https://bitbucket.org/astanin/python-tabulate
        if output_format == "json":
            output = json.dumps(entries, indent=4)

        elif output_format.startswith("tabular"):
            table_format = get_table_format(output_format)
            entries = compact_table(to_table(entries), output_format)
            output = tabulate(entries, headers="keys", tablefmt=table_format)

        else:
            raise ValueError(f"Unknown output format \"{output_format}\"")

        print(output)


def get_table_format(output_format):
    tablefmt = None
    if output_format is not None and output_format.startswith("tabular"):
        try:
            tablefmt = output_format.split(":")[1]
        except:
            tablefmt = "psql"

    return tablefmt


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
