import zipfile
import io
import csv
import functools

import common

#this module fetches chrome os version numbers from the MercuryWorkshop/chromeos-versions repo

versions_url = "https://nightly.link/MercuryWorkshop/chromeos-versions/workflows/build/main/data.zip"

def fetch_all_versions():
  print(f"GET {versions_url}")
  response = common.session.get(versions_url, follow_redirects=True)
  zip_buffer = io.BytesIO(response.content)

  with zipfile.ZipFile(zip_buffer, "r") as z:
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
