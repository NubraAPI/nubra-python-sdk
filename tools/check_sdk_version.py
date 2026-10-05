"""Compare the installed nubra-sdk with the version these examples were tested against and with PyPI.

    py -3.12 tools/check_sdk_version.py
"""
import json
import urllib.request
from importlib import metadata

TESTED_SDK_VERSION = "0.5.4"


def key(v):
    return tuple(int(p) for p in v.split(".") if p.isdigit())


try:
    installed = metadata.version("nubra-sdk")
except metadata.PackageNotFoundError:
    raise SystemExit("nubra-sdk is not installed. Run: python -m pip install nubra-sdk")

try:
    latest = json.load(urllib.request.urlopen("https://pypi.org/pypi/nubra-sdk/json", timeout=10))["info"]["version"]
except Exception:
    latest = None

print(f"Installed nubra-sdk : {installed}")
print(f"Examples tested on  : {TESTED_SDK_VERSION}")
print(f"Latest on PyPI      : {latest or 'unknown (offline?)'}")

if key(installed) < key(TESTED_SDK_VERSION):
    print("\nYour SDK is older than the examples. Upgrade: python -m pip install --upgrade nubra-sdk")
elif latest and key(latest) > key(TESTED_SDK_VERSION):
    print(f"\nA newer SDK ({latest}) exists than the one these examples were tested on. See VERSIONS.md.")
else:
    print("\nUp to date.")
