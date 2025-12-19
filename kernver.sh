#!/bin/bash

set -e

temp_dir="$(mktemp -d)"
linux_version_regex='(\d+\.\d+\.\d+-\d+-[0-9a-g]+)|Linux version (\d+\.\d+\.\d+-?\d*-?[0-9a-g]*)'

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

stream_zip() {
  local img_url="$1"
  local mime_type="$(check_file_type "$img_url")"

  if [ "$mime_type" = "application/zip" ]; then
    curl -s "$img_url" | busybox unzip - -p 2>/dev/null 

  #sometimes the zip file is inside a gzip file for some reason
  elif [ "$mime_type" = "application/gzip" ]; then
    curl -s "$img_url" | gzip -d 2>/dev/null | busybox unzip - -p 2>/dev/null 

  else
    echo "error: invalid mime type of $mime_type" 1>&2
    exit 1
  fi
}

grep_regex() {
  if [ "$(command -v pcregrep)" ]; then
    pcregrep "$@"
  else
    pcre2grep "$@"
  fi
}

grep_regex_strict() {
  grep_regex "$@" | tail -n1 | (! grep '')
}

get_linux_version() {
  local kernel_bin="$1"
  strings "$kernel_bin" \
    | grep_regex_strict -o1 -o2 "$linux_version_regex" || return 0
  
  local binwalk_out="$(cd "$temp_dir"; binwalk --extract "$kernel_bin")"
  strings "$temp_dir"/*.extracted/* \
    | grep_regex_strict -o1 -o2 "$linux_version_regex" || return 0
  
  local lz4_offset="$(echo "$binwalk_out" | grep_regex -o1 "(\d+).+?LZ4 compressed data" | head -n1)"
  dd if="$kernel_bin" iflag=skip_bytes,count_bytes skip="$lz4_offset" status=none \
    | lz4 -d \
    | strings \
    | grep_regex_strict -o1 -o2 "$linux_version_regex" || return 0
  
  echo "error: could not find linux kernel version" 1>&2
  return 1
}

get_kernver() {
  local img_url="$1"
  local img_bin="$temp_dir/image.bin"
  local kernel_bin="$temp_dir/kernel.bin"

  truncate "$img_bin" -s "10G"
  stream_zip "$img_url" \
    | dd of="$img_bin" iflag=fullblock bs=1M count=1 conv=notrunc status=none

  local fdisk_out="$(fdisk -l "$img_bin" 2>/dev/null | grep "${img_bin}4")"
  local start="$(echo "$fdisk_out" | awk '{print $2}')"
  local sectors="$(echo "$fdisk_out" | awk '{print $4}')"

  stream_zip "$img_url" \
    | dd of="$kernel_bin" iflag=fullblock,skip_bytes,count_bytes \
        oflag=count_bytes bs=1M skip="$((start*512))" \
        count="$((sectors*512))" status=none

  #tpm_kernver
  futility show "$kernel_bin" | grep "Kernel version:" | awk '{print $3}'
  #linux kernel version number
  get_linux_version "$kernel_bin"

  rm -f "$img_bin" "$kernel_bin"
}

trap clean_up EXIT

get_kernver "$1"