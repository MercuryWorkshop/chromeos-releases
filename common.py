import pathlib
from collections import defaultdict

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

base_path = pathlib.Path(__file__).resolve().parent

session = requests.Session()
retry = Retry(connect=10, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

versions = {}
dates = {}
hwid_matches = defaultdict(set)
device_names = defaultdict(set)
