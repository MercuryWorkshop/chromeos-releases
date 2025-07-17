import pathlib
import sqlite3
import json
from collections import defaultdict
from datetime import datetime

import requests

base_path = pathlib.Path(__file__).resolve().parent
downloads_path = base_path / "downloads" / "chrome100"

chrome100_db_path = downloads_path / "chrome100.db"
chrome100_db_url = "https://cdn.jsdelivr.net/npm/chrome-versions@1.1.5/dist/chrome.db"
chrome100_dl_template = "https://dl.google.com/dl/edgedl/chromeos/recovery/chromeos_{platform}_{board}_recovery_{channel}_{mp_token}{mp_key}.bin.zip"

def fetch_chrome100_db():
  if chrome100_db_path.exists():
    return
  print(f"GET {chrome100_db_url}")
  db_response = requests.get(chrome100_db_url)
  chrome100_db_path.write_bytes(db_response.content)

def read_chrome100_db():
  conn = sqlite3.connect(chrome100_db_path)
  conn.row_factory = sqlite3.Row
  db = conn.cursor()

  rows = db.execute(f"SELECT * from cros_recovery_image")
  raw_data = [dict(row) for row in rows]
  conn.close()

  data = defaultdict(list)
  for image_data in raw_data:
    board = image_data["board"]
    if not board in data:
      data[board] = []

    image_data["mp_key"] = "" if image_data["mp_key"] == 1 else f"-v{image_data['mp_key']}"
    last_modified_dt = datetime.strptime(image_data["last_modified"], "%Y-%m-%dT%H:%M:%SZ")
    last_modified = int((last_modified_dt - datetime(1970, 1, 1)).total_seconds())

    image = {
      "platform_version": image_data["platform"],
      "chrome_version": image_data["chrome"],
      "channel": image_data["channel"],
      "last_modified": last_modified,
      "url": chrome100_dl_template.format(**image_data)
    }
    data[board].append(image)

  return data

def get_chrome100_data():
  downloads_path.mkdir(exist_ok=True)
  fetch_chrome100_db()
  chrome100_data = read_chrome100_db()
  
  return chrome100_data

if __name__ == "__main__":
  get_chrome100_data()