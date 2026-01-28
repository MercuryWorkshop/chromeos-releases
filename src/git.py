import json
from datetime import datetime

from dulwich.object_store import tree_lookup_path
from dulwich import porcelain

import wayback
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
  
def migrate_to_git():
  print("Migrating wayback snapshots to git repo...")
  clone_repo()

  wayback_files = []
  for path in wayback.downloads_path.rglob("*.json"):
    if not path.stem.isdigit():
      continue
    dt = datetime.strptime(path.stem, "%Y%m%d%H%M%S")
    wayback_files.append((dt, path))
  wayback_files.sort()

  print("Creating git commits...")
  with porcelain.open_repo_closing(repo_path) as repo:
    for dt, path in wayback_files:
      relative_path = path.relative_to(wayback.downloads_path)
      new_path = repo_path / "sources" / f"{relative_path.parent}.json"
      new_path.parent.mkdir(parents=True, exist_ok=True)
      new_path.write_bytes(path.read_bytes())

      commit_msg = f"{dt} - Update {new_path.relative_to(sources_path)}"
      porcelain.add(repo, new_path)
      porcelain.commit(repo, commit_msg, author=commit_author, committer=commit_author)
  
  print("Done migrating.")

if __name__ == "__main__":
  migrate_to_git()