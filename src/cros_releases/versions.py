import zipfile
import io
import csv
import functools
import time

from cros_releases import common

#this module fetches chrome os version numbers from the MercuryWorkshop/chromeos-versions repo

downloads_path = common.base_path / "downloads" / "versions"

versions_path = downloads_path / "versions.zip"
versions_url = "https://nightly.link/MercuryWorkshop/chromeos-versions/workflows/build/main/data.zip"

def fetch_all_versions():
  if versions_path.exists() and time.time() - versions_path.stat().st_mtime < 3600:
    return
  print(f"GET {versions_url}")
  response = common.session.get(versions_url, follow_redirects=True)
  downloads_path.mkdir(parents=True, exist_ok=True)
  versions_path.write_bytes(response.content)

def read_all_versions():
  fetch_all_versions()
  with zipfile.ZipFile(versions_path, "r") as z:
    csv_text = z.read("data.csv").decode().strip()
  reader = csv.reader(csv_text.split("\n"))
  for platform_version, chrome_version in reader:
    common.versions[platform_version] = chrome_version

def get_version_score(version):
  parts = [int(n) for n in version.split(".")]
  return parts[0] * 1_000_000 + parts[1] * 1_000 + parts[0]

#try to find the chrome version for the closest platform version
@functools.cache
def get_chrome_version(platform_version):
  if platform_version in common.versions:
    return common.versions[platform_version]

  search_score = get_version_score(platform_version)
  matches = {}
  best_match = None
  best_diff = 2_000_000
  for match_version in common.versions:
    match_score = get_version_score(match_version)
    score_diff = abs(search_score - match_score)
    if score_diff < best_diff:
      best_match = match_version
      best_diff = score_diff 
  
  if best_match:
    return common.versions[best_match]
  return None
