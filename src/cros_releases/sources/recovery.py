import json
import re
from collections import defaultdict

from cros_releases import common
from cros_releases import versions
from cros_releases import git
from cros_releases import sources

recovery_url_template = "https://dl.google.com/dl/edgedl/chromeos/recovery/{filename}"
recovery_filenames = [
  "recovery.json", "recovery2.json", "onhub_recovery.json", "workspaceHardware_recovery2.json", 
  "cloudready_recovery.json", "cloudready_recovery2.json"
]

def parse_recovery_data(snapshots):
  dl_urls = set()
  data = defaultdict(list)

  for snapshot in snapshots:
    for item in snapshot:
      matches = re.findall(common.dl_url_regex, item["url"])[0]
      platform_version, board, channel = matches
      common.hwid_matches[board].add(item["hwidmatch"])

      if "chrome_version" in item:
        chrome_version = item["chrome_version"]
      else:
        chrome_version = versions.get_chrome_version(platform_version)
        if not chrome_version:
          print(f"Warning: could not find chrome version for {item['url']}")
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
  
  sources.dates.fetch_modified_dates(data)
  return data

def fetch_recovery_data():
  snapshots = []
  for filename in recovery_filenames:
    recovery_url = recovery_url_template.format(filename=filename)
    snapshot_path = git.recovery_sources_path / filename

    print(f"GET {recovery_url}")
    response = common.session.get(recovery_url)
    response.raise_for_status()
    snapshot = response.json()
    snapshots.append(snapshot)
    snapshot_path.write_text(json.dumps(snapshot, indent=2))
  
  return parse_recovery_data(snapshots)