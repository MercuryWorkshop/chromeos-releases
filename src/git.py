import json
from datetime import datetime

import dulwich 
from dulwich import porcelain

import wayback
import common

repo_path = common.data_path / "repo"
sources_path = repo_path / "sources"
repo_url = "https://github.com/MercuryWorkshop/chromeos-releases-data"
commit_author="GitHub Actions <>"

commits_api_url = "https://api.github.com/repos/MercuryWorkshop/chromeos-releases-data/commits?path=data.json"
file_url_template = "https://raw.githubusercontent.com/MercuryWorkshop/chromeos-releases-data/{commit}/data.json"

downloads_path = common.base_path / "downloads" / "git"

def get_git_data():
  downloads_path.mkdir(exist_ok=True, parents=True)

  print(f"GET {commits_api_url}")
  response = common.session.get(commits_api_url)
  commits_data = response.json()

  data_sources = []
  for commit_data in commits_data:
    commit_hash = commit_data["sha"]
    file_url = file_url_template.format(commit=commit_hash)
    file_path = downloads_path / f"{commit_hash}.json"

    if file_path.exists():
      file_data = json.loads(file_path.read_text())

    else:
      print(f"GET {file_url}")
      file_response = common.session.get(file_url)
      file_data = file_response.json()
      file_path.write_text(json.dumps(file_data))
    
    data = {}
    for board_name, board_data in file_data.items():
      images = board_data["images"]
      data[board_name] = list(filter(lambda x: x["platform_version"] != "0.0.0", images))
    data_sources.append(data)
  
  return data_sources


def migrate_to_git():
  print("Migrating wayback snapshots to git repo...")
  if not repo_path.exists():
    print(f"Cloning {repo_url}")
    porcelain.clone(repo_url, repo_path)
    print("\nDone cloning.")
  
  wayback_files = []
  for path in wayback.downloads_path.rglob("*.json"):
    if not path.stem.isdigit():
      continue
    dt = datetime.strptime(path.stem, "%Y%m%d%H%M%S")
    wayback_files.append((dt, path))
  wayback_files.sort()

  print("Creating git commits...")
  repo = dulwich.repo.Repo(repo_path)

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