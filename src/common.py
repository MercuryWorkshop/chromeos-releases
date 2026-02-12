import pathlib
from collections import defaultdict

import httpx
from httpx_retries import Retry, RetryTransport

src_path = pathlib.Path(__file__).resolve().parent
scripts_path = src_path / "scripts"
base_path = src_path.parent
data_path = base_path / "data"

retry = Retry(total=10, backoff_factor=0.5)
transport = RetryTransport(retry=retry)
session = httpx.Client(transport=transport, http2=True)
session.headers.update({
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0"
})

versions = {}
dates = {}
hwid_matches = defaultdict(set)
device_names = defaultdict(set)

#copied from https://www.chromium.org/chromium-os/developer-library/reference/development/developer-information-for-chrome-os-devices/
brand_name_overrides = {
  "whirlwind": ["OnHub Router TGR1900"],
  "arkham": ["OnHub SRT-AC1900"],
  "gale": ["Google WiFi"],
  "mistral": ["Nest Wifi router"]
}

recovery_url_template = "https://dl.google.com/dl/edgedl/chromeos/recovery/{filename}"
recovery_filenames = [
  "recovery.json", "recovery2.json", "onhub_recovery.json", "workspaceHardware_recovery2.json", 
  "cloudready_recovery.json", "cloudready_recovery2.json"
]

dash_url_template = "https://chromiumdash.appspot.com/cros/fetch_serving_builds?deviceCategory={category}"
dash_categories = ["Chrome OS", "ChromeOS", "Chrome OS Flex", "ChromeOS Flex", "Google Meet Hardware"]

class HashableImageDict(dict):
  def __hash__(self):
    return hash(self["url"])
