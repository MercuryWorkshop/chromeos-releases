from collections import defaultdict

from cros_releases import git
from cros_releases import sources

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

def parse_dash_snapshots(snapshots_dir):
  dl_urls = set()

  for snapshot in git.get_snapshots(snapshots_dir):
    for board, board_data in snapshot["builds"].items():
      parse_board_data(board, board_data, dl_urls)
  
  data = defaultdict(list)
  for dl_url in dl_urls:
    matches = re.findall(dl_url_regex, dl_url)[0]
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


def get_dash_data():
  clone_repo()
  return parse_recovery_data(sources_path / "recovery")

def save_dash_data():
  pass