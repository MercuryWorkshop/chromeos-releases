import json
import shutil
from datetime import timezone, datetime

from dulwich.object_store import tree_lookup_path
from dulwich import porcelain

import wayback
import kernver
import common

repo_path = common.data_path / "repo"
sources_path = repo_path / "sources"
repo_url = "https://github.com/MercuryWorkshop/chromeos-releases-data"
commit_author="GitHub Actions <>"

def clone_repo():
  common.data_path.mkdir(exist_ok=True)
  if not repo_path.exists():
    print(f"Cloning {repo_url}")
    porcelain.clone(repo_url, repo_path)
    print("\nDone cloning.")

def get_past_revisions(path):
  with porcelain.open_repo_closing(repo_path) as repo:
    for entry in repo.get_walker(paths=[path.encode()]):
      commit = entry.commit
      mode, sha = tree_lookup_path(repo.get_object, commit.tree, path.encode())
      yield repo[sha].data

def get_git_data():
  clone_repo()
  data_sources = []
  for json_data in get_past_revisions("data.json"):
    data = json.loads(json_data)
    for board_name, board_data in data.items():
      images = board_data["images"]
      data[board_name] = list(filter(lambda x: x["platform_version"] != "0.0.0", images))
    data_sources.append(data)
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
  new_kerver_path = sources_path / "kernver.json"
  migrated_files.append((dt_now, kernver.dl_kernver_path, new_kerver_path))

  #migrate recovery image date data
  new_dates_path = sources_path / "dates.json"
  migrated_files.append((dt_now, wayback.dl_dates_path, new_dates_path))

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