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
            if r.status >= 400:
                broken.append((p["id"], r.status))
    except urllib.error.HTTPError as err:
        broken.append((p["id"], err.code))
    except Exception as err:  # network errors count as broken
        broken.append((p["id"], type(err).__name__))

print(f"checked {len(sample)} affiliate links, {len(broken)} broken")
for pid, why in broken[:20]:
    print(f"  {pid}: {why}")
sys.exit(1 if len(broken) > max(1, len(sample) // 10) else 0)
