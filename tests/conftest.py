import os
import sys
from pathlib import Path

import pytest
from grafana_api.grafana_api import GrafanaClientError

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


@pytest.fixture(scope='session')
def docker_services_project_name(pytestconfig):
    return "pytest_grafana-wtf"


@pytest.fixture(scope='session')
def docker_grafana(docker_services):
    """
    Start Grafana service.
    """
    docker_services.start('grafana')
    public_port = docker_services.wait_for_service("grafana", 3000)
    url = "http://{docker_services.docker_ip}:{public_port}".format(**locals())
    return url


@pytest.fixture
def create_datasource(docker_grafana):
    # https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures
    def _create_datasource(name: str, type: str, access: str):
        grafana = GrafanaWtf.grafana_client_factory(docker_grafana)
        # TODO: Add fixture which completely resets everything in Grafana before running the test harness.
        #       Move to a different port than 3000 then!
        try:
            grafana.datasource.create_datasource(dict(name=name, type=type, access=access))
        except GrafanaClientError as ex:
            if "Client Error 409: data source with the same name already exists" not in str(ex):
                raise
    return _create_datasource


clean_environment()
