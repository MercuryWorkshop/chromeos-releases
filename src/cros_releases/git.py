import json
import shutil
import re
from collections import defaultdict
from datetime import timezone, datetime

from dulwich.object_store import tree_lookup_path
from dulwich import porcelain

from cros_releases import versions
from cros_releases import wayback
from cros_releases import common

repo_path = common.data_path / "repo"
sources_path = repo_path / "sources"
repo_url = "https://github.com/MercuryWorkshop/chromeos-releases-data"
commit_author="GitHub Actions <>"

dl_url_regex = r"https://dl\.google\.com/dl/edgedl/chromeos/recovery/chromeos_([\d\.]+?)_(.+?)_recovery_(.+?)_.+?\.bin\.zip"
dl_dates_path = sources_path / "dates.json"
dl_kernver_path = sources_path / "kernver.json"

def clone_repo():
  common.data_path.mkdir(exist_ok=True)
  if not repo_path.exists():
    print(f"Cloning {repo_url}")
    porcelain.clone(repo_url, repo_path)
    print("\nDone cloning.")

def get_past_revisions(path):
  with porcelain.open_repo_closing(repo_path) as repo:
    for entry in repo.get_walker(paths=[str(path).encode()]):
      commit = entry.commit
      mode, sha = tree_lookup_path(repo.get_object, commit.tree, path.encode())
      yield repo[sha].data

def get_snapshots(snapshots_dir):
  for json_path in snapshots_dir.rglob("*.json"):
    for snapshot_data in get_past_revisions(json_path):
      yield json.loads(snapshot_data)

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

  for snapshot in get_snapshots(snapshots_dir):
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
  
  fetch_modified_dates(data)
  return data

def prase_recovery_data(snapshots_dir):
  dl_urls = set()
  data = defaultdict(list)

  for snapshot in get_snapshots(snapshots_dir):
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
  
  fetch_modified_dates(data)
  return data

def fetch_modified_dates(data):
  dates = {}
  if dl_dates_path.exists():
    dates = json.loads(dl_dates_path.read_text())
  
  for board, images in data.items():
    for image in images:
      dl_url = image["url"]
      
      if dl_url in dates:
        last_modified = dates[dl_url]
      elif dl_url in common.dates:
        last_modified = common.dates[dl_url]
      
      else:
        print(f"HEAD {dl_url}")
        dl_response = common.session.head(dl_url)
        timestamp_raw = dl_response.headers["Last-Modified"]
        
        timestamp_pattern = "%a, %d %b %Y %H:%M:%S %Z"
        last_modified_dt = datetime.strptime(timestamp_raw, timestamp_pattern).replace(tzinfo=timezone.utc)
        last_modified = int(last_modified_dt.timestamp())
        dates[dl_url] = last_modified
      
      image["last_modified"] = last_modified
  
  dates = dict(sorted(dates.items(), key=lambda x: x[1]))
  dl_dates_path.write_text(json.dumps(dates, indent=2))
  common.dates.update(dates)

def get_git_data():
  clone_repo()
  data_sources = []

  for json_data in get_past_revisions("data.json"):
    data = json.loads(json_data)
    for board_name, board_data in data.items():
      images = board_data["images"]
      data[board_name] = list(filter(lambda x: x["platform_version"] != "0.0.0", images))
    data_sources.append(data)

  data_sources.append(parse_dash_snapshots(sources_path / "dash"))
  data_sources.append(prase_recovery_data(sources_path / "recovery"))

  return data_sources

def make_commit(repo, path, dt):
  commit_msg = f"{dt.replace(tzinfo=None)} - Update {path.relative_to(repo_path)}"
  porcelain.add(repo, path)
  porcelain.commit(
    repo, message=commit_msg, author=commit_author, committer=commit_author,
    commit_timestamp=dt.timestamp(), author_timezone=0, commit_timezone=0
  )

def migrate_to_git():
  print("Migrating wayback snapshots to git repo...")
  clone_repo()

  #migrate wayback snapshots
  migrated_files = []
  dt_now = datetime.utcnow().replace(microsecond=0, tzinfo=timezone.utc)
  for path in wayback.downloads_path.rglob("*.json"):
    if not path.stem.isdigit():
      continue
    dt = datetime.strptime(path.stem, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    relative_path = path.relative_to(wayback.downloads_path)
    new_path = repo_path / "sources" / f"{relative_path.parent}.json"
    migrated_files.append((dt, path, new_path))
  
  #migrate kernver data
  old_kernver_path = common.downloads_path / "kernver" / "kernver.json"
  migrated_files.append((dt_now, old_kernver_path, dl_kernver_path))
  #migrate recovery image date data
  old_dates_path = common.downloads_path / "wayback" / "dates.json"
  migrated_files.append((dt_now, old_dates_path, dl_dates_path))

  migrated_files.sort()
  print("Creating git commits...")

  with porcelain.open_repo_closing(repo_path) as repo:
    for dt, old_path, new_path in migrated_files:
      new_path.parent.mkdir(parents=True, exist_ok=True)
      shutil.copy(old_path, new_path)
      make_commit(repo, new_path, dt)
  
  print("Done migrating.")

if __name__ == "__main__":
  migrate_to_git()