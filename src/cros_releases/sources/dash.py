import json
import re
from collections import defaultdict

from cros_releases import common
from cros_releases import versions
from cros_releases import git
from cros_releases import sources

dash_url_template = "https://chromiumdash.appspot.com/cros/fetch_serving_builds?deviceCategory={category}"
dash_categories = ["Chrome OS", "ChromeOS Flex", "Google Meet Hardware"]

def parse_board_data(board, board_data, dl_urls):
  for key, value in board_data.items():
    if key == "pushRecoveries":
      dl_urls |= set(value.values())
    elif key == "brandNames":
      common.device_names[board] |= set(value)

    elif isinstance(value, dict):
      if "version" in value:
        if not value["version"] in common.versions:
          common.versions[value["version"]] = value["chromeVersion"]
      else:
        parse_board_data(board, value, dl_urls)

def parse_dash_snapshots(snapshots):
  dl_urls = set()

  for snapshot in snapshots:
    for board, board_data in snapshot["builds"].items():
      parse_board_data(board, board_data, dl_urls)
  
  data = defaultdict(list)
  for dl_url in dl_urls:
    matches = re.findall(common.dl_url_regex, dl_url)[0]
    platform_version, board, channel = matches

    chrome_version = versions.get_chrome_version(platform_version)
    if not chrome_version:
      print(f"Warning: could not find chrome version for {dl_url}")
      continue

    image = {
      "platform_version": platform_version,
      "chrome_version": chrome_version,
      "channel": channel,
      "last_modified": None,
      "url": dl_url
    }
    data[board].append(image)
  
  sources.dates.fetch_modified_dates(data)
  return data

def fetch_dash_data():
  snapshots = []
  for category in dash_categories:
    dash_url = dash_url_template.format(category=category)
    snapshot_path = git.dash_sources_path / f"{category.lower().replace(' ', '_')}.json"

    print(f"GET {dash_url}")
    response = common.session.get(dash_url)
    response.raise_for_status()
    snapshot = response.json()
    snapshots.append(snapshot)
    snapshot_path.write_text(json.dumps(snapshot, indent=2))
  
  return parse_dash_snapshots(snapshots)