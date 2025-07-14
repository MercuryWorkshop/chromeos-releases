import pathlib
import sqlite3
import json
from datetime import datetime

import requests

base_path = pathlib.Path(__file__).resolve().parent
downloads_path = base_path / "downloads"
data_path = base_path / "data"

chrome100_db_path = downloads_path / "chrome100.db"
chrome100_data_path = downloads_path / "chrome100.json"
chrome100_db_url = "https://cdn.jsdelivr.net/npm/chrome-versions@1.1.5/dist/chrome.db"
chrome100_dl_template = "https://dl.google.com/dl/edgedl/chromeos/recovery/chromeos_{platform}_{board}_recovery_{channel}_{mp_token}{mp_key}.bin.zip"

def fetch_chrome100_data():
  print(f"Downloading {chrome100_db_url}")
  db_request = requests.get(chrome100_db_url)
  chrome100_db_path.write_bytes(db_request.content)

def read_chrome100_db():
  conn = sqlite3.connect(chrome100_db_path)
  conn.row_factory = sqlite3.Row
  db = conn.cursor()

  rows = db.execute(f"SELECT * from cros_recovery_image")
  raw_data = [dict(row) for row in rows]
  conn.close()

  data = {}
  for image_data in raw_data:
    board = image_data["board"]
    if not board in data:
      data[board] = []

    image_data["mp_key"] = "" if image_data["mp_key"] == 1 else f"-v{image_data['mp_key']}"
    last_modified_dt = datetime.strptime(image_data["last_modified"], "%Y-%m-%dT%H:%M:%SZ")
    last_modified_unix = int((last_modified_dt - datetime(1970, 1, 1)).total_seconds())

    image = {
      "platform_version": image_data["platform"],
      "chrome_version": image_data["chrome"],
      "channel": image_data["channel"],
      "last_modified": image_data["last_modified"],
      "last_modified_unix": last_modified_unix,
      "url": chrome100_dl_template.format(**image_data)
    }
    data[board].append(image)
  
  data_sorted = {}
  for board, images in data.items():
    data_sorted[board] = images.sort(key=lambda x: x["last_modified_unix"])
  
  return data_sorted

def main():
  downloads_path.mkdir(exist_ok=True)
  data_path.mkdir(exist_ok=True)

  if not chrome100_db_path.exists():
    fetch_chrome100_data()
  chrome100_data = read_chrome100_db()
  chrome100_data_path.write_text(json.dumps(chrome100_data, indent=2))

if __name__ == "__main__":
  main()