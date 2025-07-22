# Chrome OS Releases Database

This repo contains scripts for building a database of all Chrome OS recovery images.

Historical data for recovery images is fetched from the [`chrome-versions`](https://www.npmjs.com/package/chrome-versions) NPM package. Newer data comes from parsing Internet Archive snapshots of the Chromium Serving Builds API. 

## Usage
Create a Python venv and install dependencies:

```
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

Run the script:

```
python3 main.py
```

## Copyright

All rights reserved.