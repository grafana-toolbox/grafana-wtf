import os
import re
from pathlib import Path

import pytest
from grafana_client.client import GrafanaClientError

from grafana_wtf.core import GrafanaWtf


def clean_environment():
    for envvar in ["GRAFANA_URL", "GRAFANA_TOKEN"]:
        try:
            del os.environ[envvar]
        except KeyError:
            pass


@pytest.fixture(scope="session")
def docker_compose_files(pytestconfig):
    """
    Override this fixture in order to specify a custom location to your `docker-compose.yml`.
    """
    return [Path(__file__).parent / "docker-compose.yml"]


@pytest.fixture(scope="session")
def docker_services_project_name(pytestconfig):
    return "pytest_grafana-wtf"


@pytest.fixture(scope="session")
def docker_grafana(docker_services):
    """
    Start Grafana service.
    """
    docker_services.start("grafana")
    public_port = docker_services.wait_for_service("grafana", 3000)
    url = "http://{docker_services.docker_ip}:{public_port}".format(**locals())
    return url


@pytest.fixture
def create_datasource(docker_grafana):
    """
    Create a Grafana data source from a test case.
    After the test case finished, it will remove the data source again.

    https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures
    """

    # Reference to `grafana-client`.
    grafana = GrafanaWtf.grafana_client_factory(docker_grafana)

    # Keep track of the datasource ids in order to delete them afterwards.
    datasource_ids = []

    def _create_datasource(name: str, type: str, access: str):
        try:
            response = grafana.datasource.create_datasource(dict(name=name, type=type, access=access))
            datasource_id = response["datasource"]["id"]
            datasource_ids.append(datasource_id)
        except GrafanaClientError as ex:
            # TODO: Mimic the original response `{'datasource': {'id': 5, 'uid': 'u9wNRyEnk', 'orgId': 1, ...`.
            #       in order to make the removal work.
            if not re.match(
                "Client Error 409: Data source with (the )?same name already exists", str(ex), re.IGNORECASE
            ):
                raise

    yield _create_datasource

    if datasource_ids:
        for datasource_id in datasource_ids:
            grafana.datasource.delete_datasource_by_id(datasource_id)


clean_environment()
