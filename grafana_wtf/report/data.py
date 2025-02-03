import json
import logging
from collections import OrderedDict
from typing import List

from grafana_wtf.report.tabular import TabularSearchReport
from grafana_wtf.util import yaml_dump

log = logging.getLogger(__name__)


def output_results(output_format: str, results: List):
    output = serialize_results(output_format, results)
    print(output)


def serialize_results(output_format: str, results: List):
    if output_format == "json":
        output = json.dumps(results, indent=4)

    elif output_format == "yaml":
        output = yaml_dump(results)

    else:
        raise ValueError(f'Unknown output format "{output_format}"')

    return output


class DataSearchReport(TabularSearchReport):
    def __init__(self, grafana_url, verbose=False, format=None):  # noqa: A002
        self.grafana_url = grafana_url
        self.verbose = verbose
        self.format = format

    def display(self, expression, result):
        expression = expression or "*"
        log.info(f"Searching for expression '{expression}' at Grafana instance {self.grafana_url}")

        output = OrderedDict(
            meta=OrderedDict(
                grafana=self.grafana_url,
                expression=expression,
            ),
            datasources=self.get_output_items(
                "Datasource", result.datasources, self.compute_url_datasource
            ),
            dashboards=self.get_output_items(
                "Dashboard", result.dashboards, self.compute_url_dashboard
            ),
        )
        output_results(self.format, output)
