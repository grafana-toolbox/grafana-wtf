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

    - https://grafana.com/docs/grafana/latest/http_api/data_source/
    - https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures
    """

    # Reference to `grafana-client`.
    grafana = GrafanaWtf.grafana_client_factory(docker_grafana)

    # Keep track of the datasource ids in order to delete them afterwards.
    datasource_ids = []

    def _create_datasource(name: str, type: str, access: str, **kwargs):
        datasource = dict(name=name, type=type, access=access)
        datasource.update(kwargs)
        try:
            response = grafana.datasource.create_datasource(datasource)
            datasource_id = response["datasource"]["id"]
            datasource_ids.append(datasource_id)
        except GrafanaClientError as ex:
            # TODO: Mimic the original response in order to make the removal work.
            # `{'datasource': {'id': 5, 'uid': 'u9wNRyEnk', 'orgId': 1, ...`.
            if not re.match(
                "Client Error 409: Data source with (the )?same name already exists", str(ex), re.IGNORECASE
            ):
                raise

    yield _create_datasource

    if datasource_ids:
        for datasource_id in datasource_ids:
            grafana.datasource.delete_datasource_by_id(datasource_id)


@pytest.fixture
def create_folder(docker_grafana):
    """
    Create a Grafana folder from a test case.
    After the test case finished, it will remove the dashboard again.

    - https://grafana.com/docs/grafana/latest/http_api/folder/
    - https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures
    """

    # Reference to `grafana-client`.
    grafana = GrafanaWtf.grafana_client_factory(docker_grafana)

    # Keep track of the dashboard uids in order to delete them afterwards.
    folder_uids = []

    # https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures
    def _create_folder(title: str, uid: str = None):

        # Create dashboard in Grafana.
        try:
            response = grafana.folder.create_folder(title=title, uid=uid)
            folder_id = response["id"]
            folder_uid = response["uid"]

            # Response is like:
            """
            {
              "id": 44,
              "uid": "iga1UrEnz",
              "title": "Testdrive",
              "url": "/dashboards/f/iga1UrEnz/testdrive",
              "hasAcl": false,
              "canSave": true,
              "canEdit": true,
              "canAdmin": true,
              "createdBy": "admin",
              "created": "2022-03-22T23:44:38Z",
              "updatedBy": "admin",
              "updated": "2022-03-22T23:44:38Z",
              "version": 1
            }
            """

            folder_uids.append(folder_uid)
            return folder_id
        except GrafanaClientError as ex:
            # TODO: Mimic the original response in order to make the removal work.
            if not re.match(
                "Client Error 409: a folder or dashboard in the general folder with the same name already exists",
                str(ex),
                re.IGNORECASE,
            ):
                raise

    yield _create_folder

    # Delete dashboard again.
    if folder_uids:
        for folder_uid in folder_uids:
            grafana.folder.delete_folder(uid=folder_uid)


@pytest.fixture
def create_dashboard(docker_grafana):
    """
    Create a Grafana dashboard from a test case.
    After the test case finished, it will remove the dashboard again.

    - https://grafana.com/docs/grafana/latest/http_api/dashboard/
    - https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures
    """

    # Reference to `grafana-client`.
    grafana = GrafanaWtf.grafana_client_factory(docker_grafana)

    # Keep track of the dashboard uids in order to delete them afterwards.
    dashboard_uids = []

    # https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures
    def _create_dashboard(dashboard: dict = None, folder_id: str = None, folder_uid: str = None):

        # Create dashboard in Grafana.
        payload = {"dashboard": dashboard, "overwrite": True}
        if folder_id:
            payload["folderId"] = folder_id
        if folder_uid:
            payload["folderUid"] = folder_uid
        response = grafana.dashboard.update_dashboard(dashboard=payload)

        # Response is like:
        # {'id': 3, 'slug': 'foo', 'status': 'success', 'uid': 'iO0xgE2nk', 'url': '/d/iO0xgE2nk/foo', 'version': 1}

        dashboard_uid = response["uid"]
        dashboard_uids.append(dashboard_uid)

    yield _create_dashboard

    # Delete dashboard again.
    if dashboard_uids:
        for dashboard_uid in dashboard_uids:
            grafana.dashboard.delete_dashboard(dashboard_uid=dashboard_uid)


@pytest.fixture
def ldi_resources(create_datasource, create_folder, create_dashboard):
    """
    Create a Grafana dashboard from a test case.
    After the test case finished, it will remove the dashboard again.

    https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures
    """

    # Create LDI datasource.
    create_datasource(
        name="ldi_v2",
        type="influxdb",
        access="proxy",
        url="http://localhost:8086/",
        user="root",
        password="root",
        database="ldi_v2",
        secureJsonData={"password": "root"},
    )

    # Create folder.
    folder_id = create_folder(title="Testdrive", uid="testdrive")

    # Create LDI dashboards.
    for file in Path("tests/grafana/dashboards").glob("*.json"):
        with open(file, "r") as f:
            dashboard = json.load(f)
            create_dashboard(dashboard=dashboard, folder_id=folder_id)


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
