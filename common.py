import pathlib
from collections import defaultdict

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

base_path = pathlib.Path(__file__).resolve().parent

session = requests.Session()
session.headers.update({
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0"
})
retry = Retry(connect=10, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

versions = {}
dates = {}
hwid_matches = defaultdict(set)
device_names = defaultdict(set)
