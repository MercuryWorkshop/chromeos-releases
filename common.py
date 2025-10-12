import pathlib
from collections import defaultdict

import httpx
from httpx_retries import Retry, RetryTransport

base_path = pathlib.Path(__file__).resolve().parent

retry = Retry(total=10, backoff_factor=0.5)
transport = RetryTransport(retry=retry)
session = httpx.Client(transport=transport, http2=True)
session.headers.update({
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0"
})

versions = {}
dates = {}
hwid_matches = defaultdict(set)
device_names = defaultdict(set)
