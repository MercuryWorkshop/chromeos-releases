from cros_releases import common
from cros_releases import git

googlebook_url_template = "https://dl.google.com/dl/edgedl/device/recovery/{filename}"
googlebook_filenames = ["production_recovery.json"]

def fetch_googlebook_data():
  git.googlebook_sources_path.mkdir(exist_ok=True)
  snapshots = []
  for filename in googlebook_filenames:
    recovery_url = googlebook_url_template.format(filename=filename)
    snapshot_path = git.googlebook_sources_path / filename
    snapshot = common.download_json(recovery_url, snapshot_path)
    snapshots.append(snapshot)
