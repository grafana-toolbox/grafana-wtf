import json
import os
import re
from io import StringIO
from pathlib import Path

import grafanalib.core
import pytest
from grafana_client.client import GrafanaClientError
from grafanalib._gen import write_dashboard

from grafana_wtf.core import GrafanaWtf


# Make sure development or production settings don't leak into the test suite.
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


@pytest.fixture
def create_dashboard(docker_grafana):
    """
    Create a Grafana dashboard from a test case.
    After the test case finished, it will remove the dashboard again.

    https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures
    """

    # Reference to `grafana-client`.
    grafana = GrafanaWtf.grafana_client_factory(docker_grafana)

    # Keep track of the dashboard uids in order to delete them afterwards.
    dashboard_uids = []

    # https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures
    def _create_dashboard(title: str, datasource: str):

        # Create dashboard in Grafana.
        dashboard = mkdashboard(title=title, datasource=datasource)
        response = grafana.dashboard.update_dashboard(dashboard={"dashboard": dashboard, "overwrite": True})

        # Response is like:
        # {'id': 3, 'slug': 'foo', 'status': 'success', 'uid': 'iO0xgE2nk', 'url': '/d/iO0xgE2nk/foo', 'version': 1}

        dashboard_uid = response["uid"]
        dashboard_uids.append(dashboard_uid)

    yield _create_dashboard

    # Delete dashboard again.
    if dashboard_uids:
        for dashboard_uid in dashboard_uids:
            grafana.dashboard.delete_dashboard(dashboard_uid=dashboard_uid)


def mkdashboard(title: str, datasource: str):
    """
    Build dashboard with single panel.
    """
    # datasource = grafanalib.core.DataSourceInput(name="foo", label="foo", pluginId="foo", pluginName="foo")
    panel_gl = grafanalib.core.Panel(dataSource=datasource, gridPos={"h": 1, "w": 24, "x": 0, "y": 0})
    dashboard_gl = grafanalib.core.Dashboard(title=title, panels=[panel_gl.panel_json(overrides={})])
    dashboard_json = StringIO()
    write_dashboard(dashboard_gl, dashboard_json)
    dashboard_json.seek(0)
    dashboard = json.loads(dashboard_json.read())
    return dashboard


clean_environment()
