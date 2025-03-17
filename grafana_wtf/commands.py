# -*- coding: utf-8 -*-
# (c) 2019-2023 Andreas Motl <andreas@hiveeyes.org>
# License: GNU Affero General Public License, Version 3
import logging
import os
from functools import partial
from operator import itemgetter

from docopt import DocoptExit, docopt

from grafana_wtf import __appname__, __version__
from grafana_wtf.core import GrafanaWtf
from grafana_wtf.report.data import DataSearchReport, output_results
from grafana_wtf.report.tabular import (
    TabularEditHistoryReport,
    TabularSearchReport,
    get_table_format,
)
from grafana_wtf.report.textual import TextualSearchReport
from grafana_wtf.util import (
    configure_http_logging,
    filter_with_sql,
    normalize_options,
    read_list,
    setup_logging,
)

log = logging.getLogger(__name__)


def run():
    """
    Usage:
      grafana-wtf [options] info
      grafana-wtf [options] explore datasources
      grafana-wtf [options] explore dashboards [--data-details] [--queries-only]
      grafana-wtf [options] explore permissions
      grafana-wtf [options] find [<search-expression>]
      grafana-wtf [options] replace <search-expression> <replacement> [--dry-run]
      grafana-wtf [options] log [<dashboard_uid>] [--number=<count>] [--head=<count>] [--tail=<count>] [--reverse] [--sql=<sql>]
      grafana-wtf [options] plugins list [--id=]
      grafana-wtf [options] plugins status [--id=]
      grafana-wtf [options] channels [--uid=]
      grafana-wtf [options] channels [--name=]
      grafana-wtf --version
      grafana-wtf (-h | --help)

    Options:
      --grafana-url=<grafana-url>       URL to Grafana instance
      --grafana-token=<grafana-token>   Grafana API Key token
      --select-dashboard=<uuid>         Restrict operation to dashboard by UID.
                                        Can be a list of comma-separated dashboard UIDs.
      --format=<format>                 Output format. One of textual, tabular, json, yaml.
      --cache-ttl=<cache-ttl>           Time-to-live for the request cache in seconds. [default: 3600]
      --drop-cache                      Drop cache before requesting resources
      --concurrency=<concurrency>       Run multiple requests in parallel. [default: 0]
      --dry-run                         Dry-run mode for the `replace` subcommand.
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
      grafana-wtf explore dashboards --format=json | jq '.[] | select(.datasources_missing) | .dashboard + {ds_missing: .datasources_missing[] | [.name]}'

      # Display all dashboards which use a specific data source, filtered by data source name.
      grafana-wtf explore dashboards --format=json | jq '.[] | select(.datasources | .[].name=="<datasource_name>")'

      # Display all dashboards using data sources with a specific type. Here: InfluxDB.
      grafana-wtf explore dashboards --format=json | jq '.[] | select(.datasources | .[].type=="influxdb")'

      # Display dashboards and many more details about where data source queries are happening.
      # Specifically, within "panels", "annotations", and "templating" slots.
      grafana-wtf explore dashboards --data-details --format=json

      # Display all database queries within dashboards.
      grafana-wtf explore dashboards --data-details --queries-only --format=json | jq '.[].details | values[] | .[] | .expr,.jql,.query,.rawSql | select( . != null and . != "" )'

    Find dashboards and data sources:

      # Search through all Grafana entities for string "ldi_readings".
      grafana-wtf --grafana-url=https://daq.example.org/grafana/ --grafana-token=eyJrIjoiWHg...dGJpZCI6MX0= find ldi_readings

      # Search Grafana instance for string "luftdaten", using more convenient invoking flavor.
      export GRAFANA_URL=https://daq.example.org/grafana/
      export GRAFANA_TOKEN=eyJrIjoiWHg...dGJpZCI6MX0=
      grafana-wtf find luftdaten

      # Search keyword within list of specific dashboards.
      grafana-wtf --select-dashboard=_JJ22OZZk,5iGTqNWZk find grafana-worldmap

      # Output search results in tabular format.
      grafana-wtf find luftdaten --format=tabular:psql

    Replace labels within dashboards:

      # Replace string within specific dashboard.
      grafana-wtf --select-dashboard=_JJ22OZZk replace grafana-worldmap-panel grafana-map-panel

      # Preview the changes beforehand, using the `--dry-run` option.
      grafana-wtf --select-dashboard=_JJ22OZZk replace grafana-worldmap-panel grafana-map-panel --dry-run

    Display edit history:

      # Display 50 most recent changes across all dashboards.
      grafana-wtf log --number=50

      # Display 5 most recent changes for specific dashboard.
      grafana-wtf log NP0wTOtmk --number=5

      # Output full history table in Grid format
      grafana-wtf log --format=tabular:grid

      # Output full history table in Markdown format
      grafana-wtf log --format=tabular:pipe

      # Display dashboards with only a single edit, in JSON format.
      grafana-wtf log --sql="
        SELECT uid, url, COUNT(version) as number_of_edits
        FROM dashboard_versions
        GROUP BY uid, url
        HAVING number_of_edits=1
      "

      # Display dashboards with only a single edit, in YAML format, `url` attribute only.
      grafana-wtf log --format=yaml --sql="
        SELECT url
        FROM dashboard_versions
        GROUP BY uid, url
        HAVING COUNT(version)=1
      "

    List plugins:

      # Inquire plugin list.
      grafana-wtf plugins list

      # Inquire plugin health check and metrics endpoints.
      grafana-wtf plugins status

    Cache control:

      # Use infinite cache expiration time, essentially caching forever.
      grafana-wtf find '#299c46' --cache-ttl=inf

      # Set cache expiration time to zero, essentially disabling the cache.
      grafana-wtf find geohash --cache-ttl=0

      # Setting `--cache-ttl` per environment variable `CACHE_TTL` is also possible
      export CACHE_TTL=infinite
      grafana-wtf find geohash

    """  # noqa: E501

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

    # Read cache expiration time setting, environment variable takes precedence.
    if "CACHE_TTL" in os.environ:
        cache_ttl = os.getenv("CACHE_TTL")
    else:
        cache_ttl = options["cache-ttl"]

    # Compute cache expiration time.
    try:
        cache_ttl = int(cache_ttl)
    except ValueError:
        if not cache_ttl or "infinite".startswith(cache_ttl.lower()):
            cache_ttl = None
        else:
            raise

    # Compute default output format.
    if not options.format:
        if options.find or options.replace:
            options.format = "textual"
        else:
            options.format = "json"

    # Sanity checks
    if grafana_url is None:
        raise DocoptExit(
            'No Grafana URL given. Please use "--grafana-url" option '
            'or environment variable "GRAFANA_URL".'
        )

    log.info(f"Grafana location: {grafana_url}")

    engine = GrafanaWtf(grafana_url, grafana_token)

    engine.enable_cache(expire_after=cache_ttl, drop_cache=options["drop-cache"])
    engine.enable_concurrency(int(options["concurrency"]))

    log.info(f"Grafana version: {engine.version}")

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

        if output_format.startswith("tab"):
            table_format = get_table_format(output_format)
            generator = partial(TabularSearchReport, tblfmt=table_format)
        elif output_format.startswith("text"):
            generator = TextualSearchReport
        else:
            generator = partial(DataSearchReport, format=output_format)

        report = generator(grafana_url, verbose=options.verbose)
        report.display(options.search_expression, result)

    if options.replace:
        engine.replace(options.search_expression, options.replacement, dry_run=options.dry_run)
        engine.clear_cache()

    if options.log:
        # Sanity checks.
        if output_format.startswith("tab") and options.sql:
            raise DocoptExit(
                f"Options --format={output_format} and --sql can not be used together, "
                f"only data output is supported."
            )

        entries = engine.log(dashboard_uid=options.dashboard_uid)

        if options.sql is not None:
            log.info(f"Filtering result with SQL expression: {options.sql}")
            entries = filter_with_sql(
                data=entries,
                view_name="dashboard_versions",
                expression=options.sql,
            )
        else:
            entries = sorted(entries, key=itemgetter("datetime"))

        if options.number is not None:
            limit = int(options.number)
            entries = entries[-limit:]
            options.reverse = True
        elif options.tail is not None:
            limit = int(options.tail)
            entries = entries[-limit:]
        elif options.head is not None:
            limit = int(options.head)
            entries = entries[:limit]

        if options.reverse:
            entries = list(reversed(entries))

        if output_format.startswith("tab"):
            report = TabularEditHistoryReport(data=entries)
            output = report.render(output_format)
            print(output)
        else:
            output_results(output_format, entries)

    if options.explore and options.datasources:
        results = engine.explore_datasources()

        unused_count = len(results["unused"])
        if unused_count:
            log.warning(f"Found {unused_count} unused data source(s)")

        output_results(output_format, results)

    if options.explore and options.dashboards:
        results = engine.explore_dashboards(
            with_data_details=options.data_details, queries_only=options.queries_only
        )
        output_results(output_format, results)

    if options.explore and options.permissions:
        results = engine.explore_permissions()
        output_results(output_format, results)

    if options.info:
        response = engine.info()
        output_results(output_format, response)

    if options.plugins:
        if options.list:
            if options.id:
                response = engine.plugins_list_by_id(options.id)
            else:
                response = engine.plugins_list()
        elif options.status:
            if options.id:
                response = engine.plugins_status_by_id(options.id)
            else:
                response = engine.plugins_status()
        else:
            raise DocoptExit('Subcommand "plugins" only provides "list" and "status"')
        output_results(output_format, response)

    if options.channels:
        if options.uid:
            response = engine.channels_list_by_uid(options.uid)
        elif options.name:
            response = engine.channels_list_by_name(options.name)
        else:
            response = engine.channels_list()
        output_results(output_format, response)
