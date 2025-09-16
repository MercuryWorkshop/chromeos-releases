import json

import common

#this module fetches past recovery image data from the chromeos-releases-data repo

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