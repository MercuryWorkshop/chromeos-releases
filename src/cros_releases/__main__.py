import pathlib
import json
import os
import argparse
from collections import defaultdict

from cros_releases import common
from cros_releases import versions
from cros_releases import git
from cros_releases import sources

out_file_path = git.repo_path / "data.json"

class HashableImageDict(dict):
  def __hash__(self):
    return hash(self["url"])
  def __eq__(self, other):
    return self["url"] == other["url"]

def merge_data(*data_sources):
  merged_sets = defaultdict(set)
  merged = {}

  for data in data_sources:
    for board, images in data.items():
      items = set([HashableImageDict(image) for image in images])
      merged_sets[board] |= items
  
  for board, images_set in merged_sets.items():
    images = [dict(image) for image in images_set]
    for image in images:
      image["chrome_version"] = versions.get_chrome_version(image["platform_version"])

    images.append({
      "platform_version": "0.0.0",
      "chrome_version": "0.0.0.0",
      "channel": "Credit: github.com/MercuryWorkshop/chromeos-releases-data",
      "last_modified": 0,
      "kernel_version": 0,
      "url": "https://github.com/MercuryWorkshop/chromeos-releases-data",
      "__license": "https://github.com/MercuryWorkshop/chromeos-releases-data/blob/main/LICENSE",
      "__license_info": "JSON data is licensed under the Creative Commons Attribution license. If you use this for your own projects, you must include attribution and link to the repository."
    })
    images.sort(key=lambda x: (x["last_modified"], x["platform_version"]))

    brand_names = sorted(list(common.device_names[board]))
    hwid_matches = sorted(list(common.hwid_matches[board]))

    if len(brand_names) == 0 and board in common.brand_name_overrides:
      brand_names = common.brand_name_overrides[board]

    merged[board] = {
      "images": images,
      "brand_names": brand_names,
      "hwid_matches": hwid_matches
    }
  
  return dict(sorted(merged.items()))

def main(args):
  print("Loading versions list")
  versions.read_all_versions()

  print("Updating git repo")
  git.clone_repo()
  if not git.sources_path.exists():
    git.migrate_to_git()

  print("Loading data sources")
  chrome100_data = sources.chrome100.get_chrome100_data()
  git_data = git.get_git_data()
  dash_data = sources.dash.fetch_dash_data()
  recovery_data = sources.recovery.fetch_recovery_data()

  print("Merging data sources")
  merged_data = merge_data(chrome100_data, dash_data, recovery_data, *git_data)

  print("Fetching kernel versions from image data")
  merged_data = sources.kernver.get_kernel_versions(merged_data)

  print("Done!")
  common.data_path.mkdir(exist_ok=True)
  out_file_path.write_text(json.dumps(merged_data, indent=2))

  if args.commit:
    git.commit_unstaged()

if __name__ == "__main__":
  parser = argparse.ArgumentParser(
    prog="chromeos-releases",
    description=f"A script for building a database of all Chrome OS recovery images"
  )
  parser.add_argument("--commit", action="store_true", help="Commit new changes made by the script to the git repo.")
  args = parser.parse_args()
  
  main(args)