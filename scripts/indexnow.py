#!/usr/bin/env python3
"""Tell IndexNow search engines (Bing, Yandex, Seznam, Naver) about new or changed pages after a deploy.

Usage: python scripts/indexnow.py OLD_SITEMAP NEW_SITEMAP [--first-run]

Submits only URLs that are new in NEW_SITEMAP, or journal articles whose <lastmod> changed.
Collection and brand pages change every day with prices, so they are not resubmitted daily;
they are found through the sitemap instead. With --first-run (the live site did not yet have
the key file) every URL is submitted once. Google does not use IndexNow.
Never touches affiliate links.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

HOST = "hourwright.co.uk"
ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = next((ROOT / "static" / "root").glob("*.txt"))
KEY = KEY_FILE.read_text().strip()


def entries(path):
    try:
        text = Path(path).read_text()
    except (FileNotFoundError, OSError):
        return {}
    return dict(re.findall(r"<loc>([^<]+)</loc>(?:<lastmod>([^<]*)</lastmod>)?", text))


def changed(old, new, first_run=False):
    if first_run or not old:
        return sorted(new)
    out = [u for u in new if u not in old]
    out += [u for u in new if u in old and "/journal/" in u and new[u] != old[u]]
    return sorted(set(out))


def main():
    old, new = entries(sys.argv[1]), entries(sys.argv[2])
    urls = changed(old, new, "--first-run" in sys.argv)
    if not urls:
        print("IndexNow: no new or changed pages")
        return
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY_FILE.name}",
                       "urlList": urls[:10000]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow: submitted {len(urls)} URLs, HTTP {r.status}")
    except urllib.error.HTTPError as err:  # never fail the deploy over this
        print(f"::warning::IndexNow returned HTTP {err.code} for {len(urls)} URLs")
    except Exception as err:
        print(f"::warning::IndexNow not reached: {err}")


if __name__ == "__main__":
    main()
