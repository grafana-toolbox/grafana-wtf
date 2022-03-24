# -*- coding: utf-8 -*-
# (c) 2019-2021 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import json
import logging
import os
from collections import OrderedDict
from functools import partial
from operator import itemgetter
from typing import List

from docopt import DocoptExit, docopt
from tabulate import tabulate

from grafana_wtf import __appname__, __version__
from grafana_wtf.core import GrafanaWtf
from grafana_wtf.report import WtfReport
from grafana_wtf.tabular_report import TabularReport
from grafana_wtf.util import (
    configure_http_logging,
    normalize_options,
    read_list,
    setup_logging,
    yaml_dump,
)

log = logging.getLogger(__name__)


def run():
    """
    Usage:
      grafana-wtf [options] info
      grafana-wtf [options] explore datasources
      grafana-wtf [options] explore dashboards
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


    General information:

      # Display a bunch of meta information and statistics.
      grafana-wtf info --format=yaml

      # Display Grafana version.
      grafana-wtf info --format=json | jq -r '.grafana.version'

    Explore data sources:

      # Display all data sources and the dashboards using them, as well as unused data sources.
      grafana-wtf explore datasources --format=yaml

      # Display names of unused datasources as a flat list.
      grafana-wtf explore datasources --format=json | jq -r '.unused[].datasource.name'

    Explore dashboards:

      # Display some details of all dashboards, including names of missing data sources.
      grafana-wtf explore dashboards --format=yaml

      # Display only dashboards which have missing data sources, along with their names.
      grafana-wtf explore dashboards --format=json | jq '.[] | select( .datasources_missing ) | .dashboard + {ds_missing: .datasources_missing[] | [.name]}'

      # Display all dashboards which use a specific data source, filtered by data source name.
      grafana-wtf explore dashboards --format=json | jq 'select( .[] | .datasources | .[].name=="<datasource_name>" )'

      # Display all dashboards using data sources with a specific type. Here: InfluxDB.
      grafana-wtf explore dashboards --format=json | jq 'select( .[] | .datasources | .[].type=="influxdb" )'


    Find dashboards and data sources:

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

    Replace labels within dashboards:

      # Replace string within specific dashboard.
      grafana-wtf --select-dashboard=_JJ22OZZk replace grafana-worldmap-panel grafana-map-panel

    Display edit history:

      # Display 50 most recent changes across all dashboards.
      grafana-wtf log --number=50

      # Display 5 most recent changes for specific dashboard.
      grafana-wtf log NP0wTOtmk --number=5

      # Output full history table in Grid format
      grafana-wtf log --format=tabular:grid

      # Output full history table in Markdown format
      grafana-wtf log --format=tabular:pipe

    """

    # Parse command line arguments
    options = normalize_options(docopt(run.__doc__, version=f"{__appname__} {__version__}"))

    # Setup logging
    debug = options.get("debug")
    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG
    setup_logging(log_level)

    # Debugging
    # log.debug("Options: {}".format(json.dumps(options, indent=4)))

    configure_http_logging(options)

    grafana_url = options["grafana-url"] or os.getenv("GRAFANA_URL")
    grafana_token = options["grafana-token"] or os.getenv("GRAFANA_TOKEN")

    # Compute cache expiration time.
    try:
        cache_ttl = int(options["cache-ttl"])
    except:
        if not options["cache-ttl"] or "infinite".startswith(options["cache-ttl"].lower()):
            cache_ttl = None
        else:
            raise

    # Sanity checks
    if grafana_url is None:
        raise DocoptExit(
            'No Grafana URL given. Please use "--grafana-url" option or environment variable "GRAFANA_URL".'
        )

    engine = GrafanaWtf(grafana_url, grafana_token)
    engine.enable_cache(expire_after=cache_ttl, drop_cache=options["drop-cache"])
    engine.enable_concurrency(int(options["concurrency"]))
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
            engine.scan_common()

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
        entries = sorted(entries, key=itemgetter("datetime"), reverse=True)

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
            raise ValueError(f'Unknown output format "{output_format}"')

        print(output)

    if options.explore and options.datasources:
        results = engine.explore_datasources()

        unused_count = len(results["unused"])
        if unused_count:
            log.warning(f"Found {unused_count} unused data source(s)")

        output_results(output_format, results)

    if options.explore and options.dashboards:
        results = engine.explore_dashboards()
        output_results(output_format, results)

    if options.info:
        response = engine.info()
        output_results(output_format, response)


def output_results(output_format: str, results: List):
    if output_format == "json":
        output = json.dumps(results, indent=4)

    elif output_format == "yaml":
        output = yaml_dump(results)

    else:
        raise ValueError(f'Unknown output format "{output_format}"')

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
        name = item["title"]
        if item["folder"]:
            name = item["folder"].strip() + " » " + name.strip()
        item["name"] = name.strip(" 🤓")
        # del item['url']
        del item["folder"]
        del item["title"]
        del item["version"]
        yield item


def compact_table(entries, format):
    seperator = "\n"
    if format.endswith("pipe"):
        seperator = "<br/>"
    for entry in entries:
        item = OrderedDict()
        if format.endswith("pipe"):
            link = "[{}]({})".format(entry["name"], entry["url"])
        else:
            link = "Name: {}\nURL: {}".format(entry["name"], entry["url"])
        item["Dashboard"] = seperator.join(
            [
                "Notes: {}".format(entry["message"].capitalize() or "n/a"),
                link,
            ]
        )
        item["Update"] = seperator.join(
            [
                "User: {}".format(entry["user"]),
                "Date: {}".format(entry["datetime"]),
            ]
        )
        yield item
