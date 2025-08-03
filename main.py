import pathlib
import json
from collections import defaultdict

import common
import googleblog
import chrome100
import wayback

base_path = pathlib.Path(__file__).resolve().parent
data_path = base_path / "data"
out_file_path = data_path / "data.json"

class HashableImageDict(dict):
  def __hash__(self):
    return hash(self["url"])

def merge_data(*data_sources):
  merged_sets = defaultdict(set)
  merged = {}

  for data in data_sources:
    for board, images in data.items():
      items = set(HashableImageDict(image) for image in images)
      merged_sets[board] |= items
  
  for board, images_set in merged_sets.items():
    images = [dict(image) for image in images_set]
    images.append({
      "platform_version": "0.0.0",
      "chrome_version": "Credit: github.com/MercuryWorkshop/chromeos-releases-data",
      "channel": "stable-channel",
      "last_modified": 0,
      "url": "https://github.com/MercuryWorkshop/chromeos-releases-data",
      "__licnese": "https://github.com/MercuryWorkshop/chromeos-releases-data/blob/main/LICENSE",
      "__license_info": "JSON data is licensed under the Creative Commons Attribution license. If you use this for your own projects, you must include attribution and link to the repository."
    })
    images.sort(key=lambda x: x["last_modified"])
    merged[board] = {
      "images": images,
      "brand_names": sorted(list(common.device_names[board])),
      "hwid_matches": sorted(list(common.hwid_matches[board]))
    }
  
  return dict(sorted(merged.items()))

if __name__ == "__main__":
  print("Loading data sources")
  googleblog.fetch_all_versions()
  chrome100_data = chrome100.get_chrome100_data()
  wayback_data = wayback.get_wayback_data()

  print("Merging data sources")
  merged_data = merge_data(chrome100_data, *wayback_data)

  print("Done!")
  data_path.mkdir(exist_ok=True)
  out_file_path.write_text(json.dumps(merged_data, indent=2))