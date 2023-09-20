import json
import os
import re
from io import StringIO
from json import JSONDecodeError
from pathlib import Path
from typing import List, Optional, Union

import grafanalib.core
import pytest
from grafana_client.client import GrafanaClientError
from grafanalib._gen import write_dashboard
from packaging import version

from grafana_wtf.core import GrafanaWtf

# Whether to clean up all resources provisioned to Grafana.
# Note that the test suite will not complete successfully when toggling this
# setting. It can be used when running individual test cases in order to
# investigate the resources provisioned to Grafana.
CLEANUP_RESOURCES = True


# Make sure development or production settings don't leak into the test suite.
def clean_environment():
    for envvar in ["GRAFANA_URL", "GRAFANA_TOKEN", "CACHE_TTL"]:
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
    url = "http://admin:admin@{docker_services.docker_ip}:{public_port}".format(**locals())
    return url


@pytest.fixture
def create_datasource(docker_grafana, grafana_version):
    """
    Create a Grafana data source from a test case.
    After the test case finished, it will remove the data source again.

    - https://grafana.com/docs/grafana/latest/http_api/data_source/
    - https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures

    The JSON response to `create_datasource` looks like this::

        {
          "datasource": {
            "id": 3,
            "uid": "PDF2762CDFF14A314",
            "orgId": 1,
            "name": "ldi_v2",
            "type": "influxdb",
            "typeLogoUrl": "",
            "access": "proxy",
            "url": "http://localhost:8086/",
            "password": "root",
            "user": "root",
            "database": "ldi_v2",
            "basicAuth": false,
            "basicAuthUser": "",
            "basicAuthPassword": "",
            "withCredentials": false,
            "isDefault": false,
            "jsonData": {},
            "secureJsonFields": {
              "password": true
            },
            "version": 1,
            "readOnly": false
          },
          "id": 3,
          "message": "Datasource added",
          "name": "ldi_v2"
        }
    """

    # Reference to `grafana-client`.
    grafana = GrafanaWtf.grafana_client_factory(docker_grafana)

    # Keep track of the datasource ids in order to delete them afterwards.
    datasource_ids = []

    def mkresponse(response):
        if version.parse(grafana_version) < version.parse("8"):
            return response["name"]
        else:
            return {"uid": response["uid"], "type": response["type"]}

    def _create_datasource(name: str, type: str = "testdata", access: str = "proxy", **kwargs):
        # Reuse existing datasource.
        try:
            response = grafana.datasource.get_datasource_by_name(name)
            datasource_id = response["id"]
            datasource_ids.append(datasource_id)
            return mkresponse(response)
        except GrafanaClientError as ex:
            if ex.status_code != 404:
                raise

        # Create new datasource.
        datasource = dict(name=name, type=type, access=access)
        datasource.update(kwargs)
        try:
            response = grafana.datasource.create_datasource(datasource)
            datasource_id = response["datasource"]["id"]
            datasource_ids.append(datasource_id)
            return mkresponse(response["datasource"])
        except GrafanaClientError as ex:
            # TODO: Mimic the original response in order to make the removal work.
            # `{'datasource': {'id': 5, 'uid': 'u9wNRyEnk', 'orgId': 1, ...`.
            if not re.match(
                "Client Error 409: Data source with (the )?same name already exists", str(ex), re.IGNORECASE
            ):
                raise

    yield _create_datasource

    if CLEANUP_RESOURCES:
        if datasource_ids:
            for datasource_id in datasource_ids:
                grafana.datasource.delete_datasource_by_id(datasource_id)


@pytest.fixture
def create_folder(docker_grafana):
    """
    Create a Grafana folder from a test case.
    After the test case finished, it will remove the folder again.

    - https://grafana.com/docs/grafana/latest/http_api/folder/
    - https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures

    The JSON response to `create_folder` looks like this::

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

    # Reference to `grafana-client`.
    grafana = GrafanaWtf.grafana_client_factory(docker_grafana)

    # Keep track of the folder uids in order to delete them afterwards.
    folder_uids = []

    def _create_folder(title: str, uid: str = None):
        # Reuse folder when it already exists.
        try:
            response = grafana.folder.get_folder(uid=uid)
            folder_id = response["id"]
            folder_uid = response["uid"]
            folder_uids.append(folder_uid)
            return folder_id
        except GrafanaClientError as ex:
            if ex.status_code != 404:
                raise

        # Create folder.
        try:
            response = grafana.folder.create_folder(title=title, uid=uid)
            folder_id = response["id"]
            folder_uid = response["uid"]
            folder_uids.append(folder_uid)
            return folder_id
        except GrafanaClientError as ex:
            # TODO: Mimic the original response in order to make the removal work.
            error_exists = re.match(
                "Client Error 409: a folder or dashboard in the general folder with the same name already exists",
                str(ex),
                re.IGNORECASE,
            )
            error_modified = re.match(
                "Client Error 412: The folder has been changed by someone else",
                str(ex),
                re.IGNORECASE,
            )
            if not (error_exists or error_modified):
                raise

    yield _create_folder

    # Delete folder again.
    if CLEANUP_RESOURCES:
        if folder_uids:
            for folder_uid in folder_uids:
                # Grafana 9.3 introduced a regression.
                # It returns 200 OK with an empty response body on delete operations.
                # https://github.com/panodata/grafana-wtf/pull/44
                try:
                    grafana.folder.delete_folder(uid=folder_uid)
                except JSONDecodeError:
                    pass


@pytest.fixture
def create_dashboard(docker_grafana):
    """
    Create a Grafana dashboard from a test case.
    After the test case finished, it will remove the dashboard again.

    - https://grafana.com/docs/grafana/latest/http_api/dashboard/
    - https://docs.pytest.org/en/4.6.x/fixture.html#factories-as-fixtures

    The JSON response to `update_dashboard` looks like this::

        {
          "id": 2,
          "slug": "luftdaten-info-generic-trend-v33",
          "status": "success",
          "uid": "jpVsQxRja",
          "url": "/d/jpVsQxRja/luftdaten-info-generic-trend-v33",
          "version": 1
        }
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
        dashboard_uid = response["uid"]
        dashboard_uids.append(dashboard_uid)

    yield _create_dashboard

    # Delete dashboard again.
    if CLEANUP_RESOURCES:
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

    def _ldi_resources(dashboards: List[Union[Path, str]] = None):
        # Create LDI datasource.
        create_datasource(
            name="ldi_v2",
            type="influxdb",
            access="proxy",
            uid="PDF2762CDFF14A314",
            url="http://localhost:8086/",
            user="root",
            password="root",
            database="ldi_v2",
            secureJsonData={"password": "root"},
        )

        # Create folder.
        folder_id = create_folder(title="Testdrive", uid="testdrive")

        # Create LDI dashboards.
        if dashboards:
            dashboard_files = dashboards
        else:
            dashboard_files = Path("tests/grafana/dashboards").glob("*.json")

        for file in dashboard_files:
            with open(file, "r") as f:
                dashboard = json.load(f)
                create_dashboard(dashboard=dashboard, folder_id=folder_id)

    return _ldi_resources


@pytest.fixture
def grafana_version(docker_grafana):
    """
    Return Grafana version number.
    """
    engine = GrafanaWtf(grafana_url=docker_grafana, grafana_token=None)
    engine.setup()
    grafana_version = engine.version()
    return grafana_version


def mkdashboard(title: str, datasources: Optional[List[str]] = None):
    """
    Build dashboard with multiple panels, each with a different data source.
    """
    # datasource = grafanalib.core.DataSourceInput(name="foo", label="foo", pluginId="foo", pluginName="foo")

    datasources = datasources or []

    # Build dashboard object model.
    panels = []
    for datasource in datasources:
        panel = grafanalib.core.Panel(dataSource=datasource, gridPos={"h": 1, "w": 24, "x": 0, "y": 0})
        panels.append(panel.panel_json(overrides={}))
    dashboard = grafanalib.core.Dashboard(title=title, panels=panels)

    # Render dashboard to JSON.
    dashboard_json = StringIO()
    write_dashboard(dashboard, dashboard_json)
    dashboard_json.seek(0)
    dashboard = json.loads(dashboard_json.read())
    return dashboard


clean_environment()
