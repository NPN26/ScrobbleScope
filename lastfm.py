import os
import sys
import time
import requests

API_KEY = os.environ.get("LASTFM_API_KEY", "65942bf85b318e73d50dc41cae3c7101")
BASE_URL = "http://ws.audioscrobbler.com/2.0/"
RATE_LIMIT_DELAY = 0.22  # ~4.5 req/sec, safely under Last.fm's 5/sec cap

if not API_KEY:
    sys.exit("Set the LASTFM_API_KEY environment variable first.")


def call_lastfm(method, **params):
    """One API call with basic retry on transient failures (429/5xx)."""
    params.update({"method": method, "api_key": API_KEY, "format": "json"})
    for attempt in range(3):
        resp = requests.get(BASE_URL, params=params, timeout=30)
        time.sleep(RATE_LIMIT_DELAY)
        if resp.status_code == 200:
            data = resp.json()
            if "error" in data:
                # e.g. error code 6 = "not found" - real answer, don't retry
                return None
            return data
        time.sleep(1 + attempt)  # backoff
    return None