#!/usr/bin/env python3
"""Refuses to pass until the site is fit to go public. Run before every deploy."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "config.json").read_text())
data = json.loads((ROOT / "data" / "products.json").read_text())
dist = ROOT / "dist"

blockers, warnings = [], []
for key, why in [("operator_legal_name", "legal pages must name who operates the site"),
                 ("operator_address", "privacy notice needs a postal address"),
                 ("contact_email", "contact and privacy pages need a working email"),
                 ("awin_publisher_id", "retailer home-page links are untracked without it")]:
    if not cfg.get(key):
        blockers.append(f"config.json '{key}' is empty: {why}")
if not cfg.get("launch_approved"):
    blockers.append("launch_approved is false: final live checks not yet signed off")
live = [r["name"] for r in cfg["retailers"] if r.get("status") == "live"]
if not live:
    blockers.append("no retailer has status 'live' (set it once Awin approves the programme)")
if len(data.get("products", [])) < cfg["feed"]["min_products"]:
    blockers.append(f"only {len(data.get('products', []))} products: connect at least one Awin feed")
if dist.exists():
    for f in dist.rglob("*.html"):
        if "to be added before launch]" in f.read_text(encoding="utf-8"):
            blockers.append(f"placeholder text still in {f.relative_to(dist)}")
            break
else:
    blockers.append("dist/ not built")
for key, why in [("ga4_measurement_id", "no analytics"),
                 ("email_form_action", "email signup hidden")]:
    if not cfg.get(key):
        warnings.append(f"'{key}' empty: {why}")

for w in warnings:
    print("warning:", w)
for b in blockers:
    print("BLOCKER:", b)
print("READY TO LAUNCH" if not blockers else f"{len(blockers)} blocker(s). Do not point the domain at this build yet.")
sys.exit(1 if blockers else 0)
