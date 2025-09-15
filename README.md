# Chrome OS Releases Database

This repo contains scripts for building a database of all Chrome OS recovery images. The generated data is located at the [chromeos-releases-data](https://github.com/MercuryWorkshop/chromeos-releases-data) repo, which is updated weekly. 

## Explanation

[Chrome OS recovery images](https://support.google.com/chromebook/answer/1080595?hl=en) are used to reinstall or upgrade the operating system on Chromebooks. You can use them to repair a broken installation, or downgrade to older versions. Downgrading Chrome OS can allow for older bugs and vulnerabilities to be used, which is useful if you are trying to jailbreak the device. 

However, Google only makes the newest recovery images available, making it difficult to find older builds. To obtain a list of older recovery images as well as download links, we get this data from two sources:

- Historical data for recovery images is fetched from the [chrome-versions](https://www.npmjs.com/package/chrome-versions) NPM package. This old database used a convoluted method of brute forcing download URLs and is no longer kept up to date. 
- Newer data comes from parsing Internet Archive snapshots of the Chromium Serving Builds API. Snapshots are taken daily, so it includes the data for every single recovery image since 2024. 

## Building the Database

Clone this repository, create a Python venv, and install dependencies:

```
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

Run the script:

```
python3 main.py
```

Generated data will be located at `data/data.json`. 

## Copyright

```
MercuryWorkshop/chromeos-releases: Database for Chrome OS release info and download URLs
Copyright (C) 2025 ading2210

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```
