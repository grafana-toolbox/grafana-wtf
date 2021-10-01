import os
from pathlib import Path

import pytest


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


clean_environment()
