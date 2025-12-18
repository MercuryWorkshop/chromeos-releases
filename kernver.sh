#!/bin/bash

set -e

temp_dir="$(mktemp -d)"

clean_up () {
  local status="$?"
  rm -rf "$temp_dir"
  exit "$status"
} 

check_file_type() {
  local img_url="$1"
  local filename="$(basename "$img_url")"
  curl -s --header "Range: bytes=0-$((512*1024))" "$img_url" \
    | file - -b --mime-type
}

download_partial() {
  local img_url="$1"
  local out_file="$2"
  local mime_type="$(check_file_type "$img_url")"

  if [ "$mime_type" = "application/zip" ]; then
    curl -s --header "Range: bytes=0-$((100*1024*1024))" "$img_url" \
      | busybox unzip - -p 2>/dev/null \
      | dd of="$out_file" bs=1M conv=notrunc status=none

  #sometimes the zip file is inside a gzip file for some reason
  elif [ "$mime_type" = "application/gzip" ]; then
    curl -s --header "Range: bytes=0-$((100*1024*1024))" "$img_url" \
      | gzip -d 2>/dev/null \
      | busybox unzip - -p 2>/dev/null \
      | dd of="$out_file" bs=1M conv=notrunc status=none

  else
    echo "error: invalid mime type of $mime_type" 1>&2
    exit 1
  fi
}

get_kernver() {
  local img_url="$1"
  local img_bin="$temp_dir/image.bin"
  local kernel_bin="$temp_dir/kernel.bin"

  truncate "$img_bin" -s "10G"
  download_partial "$img_url" "$img_bin"

  local fdisk_out="$(fdisk -l "$img_bin" 2>/dev/null | grep "${img_bin}4")"
  local start="$(echo "$fdisk_out" | awk '{print $2}')"
  local sectors="$(echo "$fdisk_out" | awk '{print $4}')"
  dd if="$img_bin" of="$kernel_bin" bs=512 skip="$start" count="$sectors" status=none

  futility show "$kernel_bin" | grep "Kernel version:" | awk '{print $3}'
  rm -f "$img_bin" "$kernel_bin"
}

trap clean_up EXIT

get_kernver "$1"