from collections import defaultdict

from cros_releases import versions
from cros_releases import git
from cros_releases import sources

recovery_json_url_template = "https://dl.google.com/dl/edgedl/chromeos/recovery/{filename}"

def parse_recovery_data(snapshots_dir):
  dl_urls = set()
  data = defaultdict(list)

  for snapshot in git.get_snapshots(snapshots_dir):
    for item in snapshot:
      matches = re.findall(dl_url_regex, item["url"])[0]
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

def get_recovery_data():
  clone_repo()
  return parse_recovery_data(sources_path / "recovery")

def save_recovery_data():
  pass