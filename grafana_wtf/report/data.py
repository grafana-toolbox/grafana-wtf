import json
from typing import List

from grafana_wtf.util import yaml_dump


def output_results(output_format: str, results: List):
    if output_format == "json":
        output = json.dumps(results, indent=4)

    elif output_format == "yaml":
        output = yaml_dump(results)

    else:
        raise ValueError(f'Unknown output format "{output_format}"')

    print(output)
