"""grafana-wtf: Grep through all Grafana entities"""
try:
    from importlib.metadata import PackageNotFoundError, version
except (ImportError, ModuleNotFoundError):  # pragma:nocover
    from importlib_metadata import PackageNotFoundError, version  # type: ignore[assignment,no-redef,unused-ignore]

__appname__ = "grafana-wtf"

try:
    __version__ = version(__appname__)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
