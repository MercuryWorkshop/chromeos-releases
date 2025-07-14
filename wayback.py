import pathlib
import json
import time
from urllib3.util.retry import Retry

import requests
from requests.adapters import HTTPAdapter

base_path = pathlib.Path(__file__).resolve().parent
downloads_path = base_path / "downloads" / "wayback"

chrome_dash_url = "https://chromiumdash.appspot.com/cros/fetch_serving_builds?deviceCategory=ChromeOS"
cdx_api_url = f"http://web.archive.org/cdx/search/cdx?output=json&url={chrome_dash_url}"
cdx_data_path = downloads_path / "cdx.json"

session = requests.Session()
retry = Retry(connect=10, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

def parse_wayback_cdx(cdx_data):
  timestamps = []
  timestamp_index = cdx_data[0].index("timestamp")
  for row in cdx_data[1:]:
    timestamps.append(row[timestamp_index])
  return timestamps

def fetch_wayback_cdx():
  if cdx_data_path.exists():
    cdx_json = json.loads(cdx_data_path.read_text())
    if time.time() - cdx_json["updated"] < 3600:
      return cdx_json["data"]
  
  cdx_request = session.get(cdx_api_url)
  cdx_data = cdx_request.json()
  cdx_json = {
    "updated": time.time(),
    "data": cdx_data
  }
  cdx_data_path.write_text(json.dumps(cdx_json, indent=2))
  return cdx_data

def fetch_wayback_snapshots():
  cdx_data = fetch_wayback_cdx()

  snapshots = []
  for timestamp in parse_wayback_cdx(cdx_data):
    snapshot_path = downloads_path / f"{timestamp}.json"
    
    if snapshot_path.exists():
      snapshot = json.loads(snapshot_path.read_text())
    
    else:
      identity_url = f"https://web.archive.org/web/{timestamp}id_/{chrome_dash_url}"
      print(f"Downloading {identity_url}")
      snapshot_request = session.get(identity_url)
      snapshot = snapshot_request.json()
      snapshot_path.write_text(json.dumps(snapshot, indent=2))
    
    snapshots.append(snapshot)

def get_wayback_data():
  fetch_wayback_snapshots()

if __name__ == "__main__":
  get_wayback_data()