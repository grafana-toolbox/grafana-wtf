from sys import modules

import niquests
import urllib3

# Amalgamate the module namespace to make all modules aiming
# to use `requests`, in fact use `niquests` instead.
modules["requests"] = niquests
modules["requests.adapters"] = niquests.adapters
modules["requests.sessions"] = niquests.sessions
modules["requests.exceptions"] = niquests.exceptions
modules["requests.packages.urllib3"] = urllib3
