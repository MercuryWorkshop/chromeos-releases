import subprocess
import os
import json
from concurrent.futures import ThreadPoolExecutor

import common

script_path = common.base_path / "kernver.sh"
downloads_path = common.base_path / "downloads" / "kernver"
dl_kernver_path = downloads_path / "kernver.json"

os.environ["TMPDIR"] = str(downloads_path)
kernel_versions = {}

def get_kernel_version(image):
  print(f"GET {image['url']}")
  kernver = subprocess.check_output([script_path, image["url"]])
  image["kernel_version"] = int(kernver)
  kernel_versions[image["url"]] = int(kernver)
  dl_kernver_path.write_text(json.dumps(kernel_versions, indent=2))
 
def get_kernel_versions(data):
  global kernel_versions
  queued_images = []
  if dl_kernver_path.exists():
    kernel_versions = json.loads(dl_kernver_path.read_text())

  for board in data.values():
    for image in board["images"]:
      if "kernel_version" in image:
        continue
      if image["url"] in kernel_versions:
        image["kernel_version"] = kernel_versions[image["url"]]
        continue
      queued_images.append(image)

  downloads_path.mkdir(parents=True, exist_ok=True)
  with ThreadPoolExecutor(max_workers=16) as executor:
    list(executor.map(get_kernel_version, queued_images))

  return data