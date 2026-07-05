import json
import shutil
import re
import io
from collections import defaultdict
from datetime import timezone, datetime

from dulwich.object_store import tree_lookup_path
from dulwich import porcelain

from cros_releases import versions
from cros_releases import sources
from cros_releases import common

repo_path = common.data_path / "repo"
sources_path = repo_path / "sources"
dash_sources_path = sources_path / "dash"
recovery_sources_path = sources_path / "recovery"

repo_url = "https://github.com/MercuryWorkshop/chromeos-releases-data"
commit_author="GitHub Actions <>"

dl_dates_path = sources_path / "dates.json"
dl_kernver_path = sources_path / "kernver.json"

def clone_repo():
  common.data_path.mkdir(exist_ok=True)
  if not repo_path.exists():
    print(f"Cloning {repo_url}")
    porcelain.clone(repo_url, repo_path, errstream=io.BytesIO())
    print("Done cloning.")

def repo_status():
  return porcelain.status(repo_path)

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

def get_git_data():
  clone_repo()
  data_sources = []

  for json_data in get_past_revisions("data.json"):
    data = json.loads(json_data)
    for board_name, board_data in data.items():
      images = board_data["images"]
      data[board_name] = list(filter(lambda x: x["platform_version"] != "0.0.0", images))
    data_sources.append(data)

  data_sources.append(sources.dash.parse_dash_snapshots(get_snapshots(dash_sources_path)))
  data_sources.append(sources.recovery.parse_recovery_data(get_snapshots(recovery_sources_path)))

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
  wayback_downloads_path = common.base_path / "downloads" / "wayback"

  for path in wayback_downloads_path.rglob("*.json"):
    if not path.stem.isdigit():
      continue
    dt = datetime.strptime(path.stem, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    relative_path = path.relative_to(wayback_downloads_path)
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

def commit_unstaged():
  unstaged_files = [filename.decode() for filename in repo_status().unstaged]
  unstaged_paths = [repo_path / filename for filename in unstaged_files]

  if not unstaged_files:
    print("No updated files to commit.")
    return
  
  print(f"Updated files:")
  print("\n".join(f"  {filename}" for filename in unstaged_files))

  dt_now = datetime.utcnow().replace(microsecond=0, tzinfo=timezone.utc)
  with porcelain.open_repo_closing(repo_path) as repo:
    for unstaged_path in unstaged_paths:
      make_commit(repo, unstaged_path, dt_now)