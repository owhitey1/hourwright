#!/usr/bin/env python3
"""Check that published affiliate links still resolve.

Requests up to 60 product links (spread across retailers) and fails if more
than 10% are broken, so a retailer that has delisted products, changed its
site or paused its programme is noticed within a day. Does nothing while
there are no products.
"""
import json
import random
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
products = json.loads((ROOT / "data" / "products.json").read_text()).get("products", [])
if not products:
    print("no products yet: nothing to check")
    sys.exit(0)

# 1. Every link: correct Awin structure, publisher id, advertiser id, tracking tag and product id.
import urllib.parse as up
CFG = json.loads((ROOT / "config.json").read_text())
PUBLISHER = str(CFG.get("awin_publisher_id", "3102076"))
malformed = []
for p in products:
    q = up.urlparse(p["link"]); a = dict(up.parse_qsl(q.query))
    if not (q.scheme == "https" and q.netloc == "www.awin1.com" and a.get("a") == PUBLISHER
            and a.get("clickref") == "hourwright" and p["id"].endswith("-" + a.get("p", "?")) and a.get("m")):
        malformed.append(p["id"])
print(f"structure: {len(products)} links, {len(malformed)} malformed")
for pid in malformed[:20]:
    print("  malformed:", pid)

# 2. A sample: the link must resolve to a product page on the retailer's site.
by_retailer = {}
for p in products:
    by_retailer.setdefault(p["retailer"], []).append(p)
sample = []
for items in by_retailer.values():
    sample += random.sample(items, min(len(items), 60 // len(by_retailer)))

broken = []
for p in sample:
    req = urllib.request.Request(p["link"], method="GET", headers={"User-Agent": "Mozilla/5.0 (Hourwright link check)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            final = up.urlparse(r.geturl())
            if r.status >= 400:
                broken.append((p["id"], r.status))
            elif "awin" in final.netloc or final.path in ("", "/"):
                broken.append((p["id"], f"landed on {final.netloc}{final.path or '/'}"))
    except urllib.error.HTTPError as err:
        broken.append((p["id"], err.code))
    except Exception as err:  # network errors count as broken
        broken.append((p["id"], type(err).__name__))

print(f"checked {len(sample)} affiliate links, {len(broken)} broken")
for pid, why in broken[:20]:
    print(f"  {pid}: {why}")
sys.exit(1 if malformed or len(broken) > max(1, len(sample) // 10) else 0)
