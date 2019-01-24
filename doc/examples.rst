####################
grafana-wtf examples
####################

*******
Running
*******

General
=======
::

    # Define URL and access token of Grafana instance.
    export GRAFANA_URL=https://daq.example.org/grafana/
    export GRAFANA_TOKEN=eyJrIjoiWHg...dGJpZCI6MX0=

    # Search through all Grafana entities for string "ldi_readings".
    grafana-wtf find ldi_readings


``grafana-wtf find weatherbase``
================================
::

    Searching for "expression" weatherbase at Grafana instance http://localhost:3000
    ==========================================
    Data Sources: 2 hits.
    ==========================================

    WEATHERBASE
    -----------
    http://localhost:3000/datasources/edit/6

    - database: weatherbase

    weatherbase
    -----------
    http://localhost:3000/datasources/edit/13

    - name: weatherbase
    - database: weatherbase

    ==========================================
    Dashboards: 2 hits.
    ==========================================

    luftdaten-info-map
    ------------------
    http://localhost:3000/d/s85oo0yik/luftdaten-info-map

    - dashboard.panels.[1].datasource: weatherbase
    - dashboard.templating.list.[0].datasource: weatherbase
    - dashboard.templating.list.[1].datasource: weatherbase
    - [...]

    luftdaten-info-trend
    --------------------
    http://localhost:3000/d/7TvTTAyik/luftdaten-info-trend

    - dashboard.templating.list.[0].datasource: weatherbase
    - dashboard.templating.list.[1].datasource: weatherbase
    - dashboard.templating.list.[2].datasource: weatherbase
    - [...]


``grafana-wtf find ldi_readings``
=================================
::

    Searching for expression "ldi_readings" at Grafana instance http://localhost:3000
    ==========================================
    Data Sources: 0 hits.
    ==========================================

    ==========================================
    Dashboards: 3 hits.
    ==========================================

    luftdaten-info-coverage
    -----------------------
    http://localhost:3000/d/1aOmc1sik/luftdaten-info-coverage

    - dashboard.panels.[0].targets.[0].measurement: ldi_readings

    luftdaten-info-map
    ------------------
    http://localhost:3000/d/s85oo0yik/luftdaten-info-map

    - dashboard.panels.[0].targets.[0].measurement: ldi_readings

    luftdaten-info-trend
    --------------------
    http://localhost:3000/d/7TvTTAyik/luftdaten-info-trend

    - dashboard.panels.[1].targets.[0].measurement: ldi_readings
    - dashboard.panels.[1].targets.[1].measurement: ldi_readings
    - dashboard.panels.[1].targets.[2].measurement: ldi_readings
    - [...]
