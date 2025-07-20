import pathlib
import re
import json
import urllib.parse as urlparse

import requests
import lxml.html

base_path = pathlib.Path(__file__).resolve().parent
downloads_path = base_path / "downloads" / "googleblog"

start_url = "https://chromereleases.googleblog.com/search?updated-max=2008-10-03T10:59:00-07:00&max-results=20&reverse-paginate=true"

chrome_version_regex = r"[^\.\d](\d+?\.\d+?\.\d+?\.\d+)[^\.\d]"
platform_version_regex = r"[^\.\d](\d+?\.\d+?\.\d+)[^\.\d]"

def fetch_blog_page(url):
  url_parsed = urlparse.urlparse(url)
  updated_max = urlparse.parse_qs(url_parsed.query)["updated-max"][0]

  page_info_path = downloads_path / f"{updated_max}.json"
  if page_info_path.exists():
    return json.loads(page_info_path.read_text())

  print(f"GET {url}")
  response = requests.get(url)
  document = lxml.html.fromstring(response.text)

  post_divs = document.cssselect(".post")
  versions = {}

  for post_div in post_divs:
    label_links = post_div.cssselect(".label")
    labels = [e.text_content().strip() for e in label_links]

    if "ChromeOS" not in labels and "Chrome OS" not in labels:
      continue
    
    post_text_div = post_div.cssselect("div[itemprop='articleBody']")[0]
    post_text = post_text_div.text_content().strip()
    post_text_html = lxml.html.fromstring(post_text)
    post_text = post_text_html.text_content().strip()
    
    chrome_versions = set(re.findall(chrome_version_regex, post_text))
    platform_versions = set(re.findall(platform_version_regex, post_text))
    if len(chrome_versions) != 1 or len(platform_versions) != 1:
      continue
    
    versions[platform_versions.pop()] = chrome_versions.pop()
  
  next_link = document.cssselect(".blog-pager-newer-link")[0]
  next_url = next_link.get("href")
  if next_url == "https://chromereleases.googleblog.com/":
    next_url = None
  
  page_info = {
    "versions": versions,
    "next_url": next_url
  }
  if next_url:
    page_info_str = json.dumps(page_info, indent=2)
    page_info_path.write_text(page_info_str)
  return page_info

def fetch_all_versions():
  versions = {}
  downloads_path.mkdir(exist_ok=True, parents=True)

  url = start_url
  while url:
    page_info = fetch_blog_page(url)
    url = page_info["next_url"]
    versions.update(page_info["versions"])
  
  return versions
