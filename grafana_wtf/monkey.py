# https://github.com/m0nhawk/grafana_api/pull/85/files

def update_dashboard(self, dashboard):
    """
    :param dashboard:
    :return:
    """

    # When the "folderId" is not available within the dashboard payload,
    # populate it from the nested "meta" object, if given.
    if "folderId" not in dashboard:
        if "meta" in dashboard and "folderId" in dashboard["meta"]:
            dashboard = dashboard.copy()
            dashboard["folderId"] = dashboard["meta"]["folderId"]

    put_dashboard_path = "/dashboards/db"
    r = self.api.POST(put_dashboard_path, json=dashboard)
    return r


def monkeypatch_grafana_api():
    import grafana_api.api.dashboard as dashboard
    dashboard.Dashboard.update_dashboard = update_dashboard
