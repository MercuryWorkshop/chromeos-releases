#!/bin/bash

urls=(
  "https://chromiumdash.appspot.com/cros/fetch_serving_builds?deviceCategory=ChromeOS"
  "https://chromiumdash.appspot.com/cros/fetch_serving_builds?deviceCategory=Google%20Meet%20Hardware"
  "https://chromiumdash.appspot.com/cros/fetch_serving_builds?deviceCategory=ChromeOS%20Flex"
  "https://dl.google.com/dl/edgedl/chromeos/recovery/recovery.json"
  "https://dl.google.com/dl/edgedl/chromeos/recovery/recovery2.json"
  "https://dl.google.com/dl/edgedl/chromeos/recovery/onhub_recovery.json"
  "https://dl.google.com/dl/edgedl/chromeos/recovery/workspaceHardware_recovery2.json"
  "https://dl.google.com/dl/edgedl/chromeos/recovery/cloudready_recovery.json"
  "https://dl.google.com/dl/edgedl/chromeos/recovery/cloudready_recovery2.json"
)

for url in "${urls[@]}"; do
  echo "$url"

  curl \
    https://web.archive.org/save \
    -X POST \
    -H "Accept: application/json" \
    -H "Authorization: $TOKEN" \
    -d"url=$url" \
    --retry 5
  
  echo
  sleep 20
done