#!/usr/bin/env python3
"""Check affiliate links WITHOUT requesting them.

Awin counts every request to an awin1.com link as a click, so an automated
checker that follows links creates artificial clicks for the advertiser. This
script never contacts Awin or the retailer. It checks instead:

1. every link's structure: HTTPS awin1.com product link, Hourwright's publisher
   id, an advertiser id, the `hourwright` click reference and a product id that
   matches the catalogue entry;
2. that the catalogue was refreshed from the retailer feeds recently, because
   products only stay listed while they are in the live feed (so a delisted
   product disappears at the next import rather than being linked to).

Exit 1 on any malformed link or a stale catalogue.
"""
import datetime as dt
import json
import sys
import urllib.parse as up
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data" / "products.json").read_text())
products = data.get("products", [])
CFG = json.loads((ROOT / "config.json").read_text())
PUBLISHER = str(CFG.get("awin_publisher_id", "3102076"))
MAX_AGE_HOURS = 48

if not products:
    print("no products yet: nothing to check")
    sys.exit(0)

malformed = []
for p in products:
    q = up.urlparse(p["link"])
    a = dict(up.parse_qsl(q.query))
    if not (q.scheme == "https" and q.netloc == "www.awin1.com" and a.get("a") == PUBLISHER
            and a.get("clickref") == "hourwright" and a.get("m") and p["id"].endswith("-" + a.get("p", "?"))):
        malformed.append(p["id"])
print(f"structure: {len(products)} links, {len(malformed)} malformed (no links were requested)")
for pid in malformed[:20]:
    print("  malformed:", pid)

stale = False
fetched = data.get("fetched_at")
if fetched:
    age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(fetched)
    hours = age.total_seconds() / 3600
    stale = hours > MAX_AGE_HOURS
    print(f"catalogue refreshed {hours:.0f} hours ago{' - STALE' if stale else ''}")
else:
    print("catalogue has no fetched_at time")
    stale = True

sys.exit(1 if malformed or stale else 0)
