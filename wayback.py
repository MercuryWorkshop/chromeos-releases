import pathlib
import json
import time
import re
from datetime import datetime

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

base_path = pathlib.Path(__file__).resolve().parent
downloads_path = base_path / "downloads" / "wayback"
snapshots_path = downloads_path / "snapshots"

device_categories = ["Chrome OS", "ChromeOS", "Chrome OS Flex", "ChromeOS Flex", "Google Meet Hardware"]

chrome_dash_url_template = "https://chromiumdash.appspot.com/cros/fetch_serving_builds?deviceCategory={category}"
cdx_api_url_template = "http://web.archive.org/cdx/search/cdx?output=json&url={url}"

"""
todo: also check the following urls:
  https://dl.google.com/dl/edgedl/chromeos/recovery/recovery.json
  https://dl.google.com/dl/edgedl/chromeos/recovery/recovery2.json
  https://dl.google.com/dl/edgedl/chromeos/recovery/onhub_recovery.json
  https://dl.google.com/dl/edgedl/chromeos/recovery/workspaceHardware_recovery2.json
  https://dl.google.com/dl/edgedl/chromeos/recovery/cloudready_recovery.json
  https://dl.google.com/dl/edgedl/chromeos/recovery/cloudready_recovery2.json
"""

dl_url_regex = r"https://dl\.google\.com/dl/edgedl/chromeos/recovery/chromeos_([\d\.]+?)_(.+?)_recovery_(.+?)_.+?\.bin\.zip"
dl_dates_path = downloads_path / "dates.json"

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

def fetch_wayback_cdx(category):
  cdx_data_path = downloads_path / f"{category.replace(' ', '_')}_cdx.json"

  if cdx_data_path.exists():
    cdx_json = json.loads(cdx_data_path.read_text())
    if time.time() - cdx_json["updated"] < 3600:
      return cdx_json["data"]

  chrome_dash_url = chrome_dash_url_template.format(category=category)
  cdx_api_url = cdx_api_url_template.format(url=chrome_dash_url)
  
  print(f"GET {cdx_api_url}")
  cdx_response = session.get(cdx_api_url)
  cdx_data = cdx_response.json()
  cdx_json = {
    "updated": time.time(),
    "data": cdx_data
  }
  cdx_data_path.write_text(json.dumps(cdx_json, indent=2))
  return cdx_data

def fetch_wayback_snapshots(category):
  cdx_data = fetch_wayback_cdx(category)

  snapshots = []
  for timestamp in parse_wayback_cdx(cdx_data):
    snapshot_path = snapshots_path / f"{category.replace(' ', '_')}_{timestamp}.json"
    
    if snapshot_path.exists():
      snapshot = json.loads(snapshot_path.read_text())
    
    else:
      chrome_dash_url = chrome_dash_url_template.format(category=category)
      identity_url = f"https://web.archive.org/web/{timestamp}id_/{chrome_dash_url}"

      print(f"GET {identity_url}")
      snapshot_response = session.get(identity_url)
      snapshot = snapshot_response.json()
      snapshot_path.write_text(json.dumps(snapshot, indent=2))
    
    snapshots.append(snapshot)
  
  return snapshots

def parse_board_data(board_data, dl_urls, versions):
  for key, value in board_data.items():
    if key == "pushRecoveries":
      dl_urls |= set(value.values())

    if isinstance(value, dict):
      if "version" in value:
        versions[value["version"]] = value["chromeVersion"]
      else:
        parse_board_data(value, dl_urls, versions)

def parse_wayback_snapshots(snapshots):
  versions = {}
  dl_urls = set()

  for snapshot in snapshots:
    for board, board_data in snapshot["builds"].items():
      parse_board_data(board_data, dl_urls, versions)
  
  data = {}
  for dl_url in dl_urls:
    matches = re.findall(dl_url_regex, dl_url)[0]
    platform_version, board, channel = matches

    if not platform_version in versions:
      continue

    image = {
      "platform_version": platform_version,
      "chrome_version": versions[platform_version],
      "channel": channel,
      "last_modified": None,
      "url": dl_url
    }

    if not board in data:
      data[board] = []
    data[board].append(image)
  
  return data

def fetch_modified_dates(data):
  dates = {}
  if dl_dates_path.exists():
    dates = json.loads(dl_dates_path.read_text())
  
  i = 1
  for board, images in data.items():
    for image in images:
      dl_url = image["url"]
      
      if dl_url in dates:
        last_modified = dates[dl_url]
      
      else:
        print(f"HEAD ({i}) {dl_url}")
        i += 1
        dl_response = session.head(dl_url)
        timestamp_raw = dl_response.headers["Last-Modified"]
        
        timestamp_pattern = "%a, %d %b %Y %H:%M:%S %Z"
        last_modified_dt = datetime.strptime(timestamp_raw, timestamp_pattern)
        last_modified = int((last_modified_dt - datetime(1970, 1, 1)).total_seconds())
        dates[dl_url] = last_modified
      
      image["last_modified"] = last_modified
    
    dl_dates_path.write_text(json.dumps(dates, indent=2))

def get_wayback_data():
  data_sources = []

  for category in device_categories:
    downloads_path.mkdir(exist_ok=True)
    snapshots_path.mkdir(exist_ok=True)
    snapshots = fetch_wayback_snapshots(category)
    wayback_data = parse_wayback_snapshots(snapshots)
    fetch_modified_dates(wayback_data)

  return data_sources

if __name__ == "__main__":
  get_wayback_data()