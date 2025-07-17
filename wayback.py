import pathlib
import json
import time
import re
from collections import defaultdict
from datetime import datetime

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

base_path = pathlib.Path(__file__).resolve().parent
downloads_path = base_path / "downloads" / "wayback"

recovery_json_files = [
  "recovery.json", "recovery2.json", "onhub_recovery.json", "workspaceHardware_recovery2.json", 
  "cloudready_recovery.json", "cloudready_recovery2.json"
]
device_categories = ["Chrome OS", "ChromeOS", "Chrome OS Flex", "ChromeOS Flex", "Google Meet Hardware"]

chrome_dash_url_template = "https://chromiumdash.appspot.com/cros/fetch_serving_builds?deviceCategory={category}"
recovery_json_url_template = "https://dl.google.com/dl/edgedl/chromeos/recovery/{filename}"
cdx_api_url_template = "http://web.archive.org/cdx/search/cdx?output=json&url={url}"

dl_url_regex = r"https://dl\.google\.com/dl/edgedl/chromeos/recovery/chromeos_([\d\.]+?)_(.+?)_recovery_(.+?)_.+?\.bin\.zip"
dl_dates_path = downloads_path / "dates.json"

session = requests.Session()
retry = Retry(connect=10, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

versions = {}
device_names = defaultdict(set)

def parse_wayback_cdx(cdx_data):
  timestamps = []
  timestamp_index = cdx_data[0].index("timestamp")
  for row in cdx_data[1:]:
    timestamps.append(row[timestamp_index])
  return timestamps

def fetch_wayback_cdx(cdx_api_url, path):
  cdx_data_path = path / "cdx.json"

  if cdx_data_path.exists():
    cdx_json = json.loads(cdx_data_path.read_text())
    if time.time() - cdx_json["updated"] < 3600:
      return cdx_json["data"]
  
  print(f"GET {cdx_api_url}")
  cdx_response = session.get(cdx_api_url)
  cdx_data = cdx_response.json()
  cdx_json = {
    "updated": time.time(),
    "data": cdx_data
  }
  cdx_data_path.write_text(json.dumps(cdx_json, indent=2))
  return cdx_data

def fetch_wayback_snapshots(url, path):
  cdx_api_url = cdx_api_url_template.format(url=url)
  cdx_data = fetch_wayback_cdx(cdx_api_url, path)

  snapshots = []
  for timestamp in parse_wayback_cdx(cdx_data):
    snapshot_path = path / f"{timestamp}.json"
    
    if snapshot_path.exists():
      snapshot = json.loads(snapshot_path.read_text())
    
    else:
      identity_url = f"https://web.archive.org/web/{timestamp}id_/{url}"

      print(f"GET {identity_url}")
      snapshot_response = session.get(identity_url)
      snapshot = snapshot_response.json()
      snapshot_path.write_text(json.dumps(snapshot, indent=2))
    
    snapshots.append(snapshot)
  
  return snapshots

def parse_board_data(board, board_data, dl_urls):
  for key, value in board_data.items():
    if key == "pushRecoveries":
      dl_urls |= set(value.values())
    elif key == "brandNames":
      device_names[board] |= set(value)

    elif isinstance(value, dict):
      if "version" in value:
        versions[value["version"]] = value["chromeVersion"]
      else:
        parse_board_data(board, value, dl_urls)

def parse_dash_snapshots(snapshots):
  dl_urls = set()

  for snapshot in snapshots:
    for board, board_data in snapshot["builds"].items():
      parse_board_data(board, board_data, dl_urls)
  
  data = defaultdict(list)
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
    data[board].append(image)
  
  return data

def prase_recovery_data(snapshots):
  dl_urls = set()
  data = defaultdict(list)

  for snapshot in snapshots:
    for item in snapshot:
      matches = re.findall(dl_url_regex, item["url"])[0]
      platform_version, board, channel = matches

      if "chrome_version" in item:
        chrome_version = item["chrome_version"]
      else:
        if platform_version in versions:
          chrome_version = versions[platform_version]
        else:
          continue

      image = {
        "platform_version": platform_version,
        "chrome_version": chrome_version,
        "channel": channel,
        "last_modified": None,
        "url": item["url"]
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
  downloads_path.mkdir(exist_ok=True)

  for category in device_categories:
    category_path = downloads_path / "dash" / category.lower().replace(" ", "_")
    category_path.mkdir(exist_ok=True, parents=True)

    chrome_dash_url = chrome_dash_url_template.format(category=category)
    dash_snapshots = fetch_wayback_snapshots(chrome_dash_url, category_path)

    dash_data = parse_dash_snapshots(dash_snapshots)
    fetch_modified_dates(dash_data)
    data_sources.append(dash_data)
  
  for filename in recovery_json_files:
    recovery_name = filename.split(".")[0]
    recovery_path = downloads_path / "recovery" / recovery_name
    recovery_path.mkdir(exist_ok=True, parents=True)

    recovery_url = recovery_json_url_template.format(filename=filename)
    recovery_snapshots = fetch_wayback_snapshots(recovery_url, recovery_path)

    recovery_data = prase_recovery_data(recovery_snapshots)
    fetch_modified_dates(recovery_data)
    data_sources.append(recovery_data)

  return data_sources

if __name__ == "__main__":
  get_wayback_data()