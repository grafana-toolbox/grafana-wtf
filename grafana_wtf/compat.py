import niquests
import requests_cache


class CachedSession(requests_cache.session.CacheMixin, niquests.Session):
    """
    Make Niquests compatible with Requests-Cache.
    """

    pass
