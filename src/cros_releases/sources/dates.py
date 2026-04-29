import json
from datetime import datetime, timezone

from cros_releases import common

downloads_path = common.downloads_path / "dates"
dl_dates_path = downloads_path / "dates.json"

def fetch_modified_dates(data):
  dates = {}
  if dl_dates_path.exists():
    dates = json.loads(dl_dates_path.read_text())
  
  i = 1
  for board, images in data.items():
    for image in images:
      dl_url = image["url"]
      
      if dl_url in dates:
        last_modified = dates[dl_url]
      elif dl_url in common.dates:
        last_modified = common.dates[dl_url]
      
      else:
        print(f"HEAD ({i}) {dl_url}")
        i += 1
        dl_response = common.session.head(dl_url)
        timestamp_raw = dl_response.headers["Last-Modified"]
        
        timestamp_pattern = "%a, %d %b %Y %H:%M:%S %Z"
        last_modified_dt = datetime.strptime(timestamp_raw, timestamp_pattern).replace(tzinfo=timezone.utc)
        last_modified = int(last_modified_dt.timestamp())
        dates[dl_url] = last_modified
      
      image["last_modified"] = last_modified
  
  dates = dict(sorted(dates.items(), key=lambda x: x[1]))
  downloads_path.mkdir(parents=True, exist_ok=True)
  dl_dates_path.write_text(json.dumps(dates, indent=2))
  common.dates.update(dates)
