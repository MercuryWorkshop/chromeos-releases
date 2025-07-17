import pathlib
import json
from collections import defaultdict

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
    images.sort(key=lambda x: x["last_modified"])
    merged[board] = images
  
  return dict(sorted(merged.items()))

if __name__ == "__main__":
  print("Loading data sources")
  chrome100_data = chrome100.get_chrome100_data()
  wayback_data = wayback.get_wayback_data()

  print("Merging data sources")
  merged_data = merge_data(chrome100_data, *wayback_data)

  print("Done!")
  data_path.mkdir(exist_ok=True)
  out_file_path.write_text(json.dumps(merged_data, indent=2))