#!/usr/bin/env python3
"""Validate every editorial file against the live catalogue.

Exit code 1 when a published article has an error or a flag (missing product,
out of stock, price above its ceiling), so the scheduled monitor emails the
owner. Drafts are reported but never fail the run.
Writes a Markdown report to $GITHUB_STEP_SUMMARY when run in GitHub Actions.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import editorial  # noqa: E402

catalogue = editorial.load_catalogue(os.environ.get("HW_DATA") or ROOT / "data" / "products.json")
today = dt.date.today()
articles = editorial.load_articles()
slugs = {}
lines = ["# Editorial check", "", f"{len(articles)} files, catalogue of {len(catalogue)} products, {today.isoformat()}", ""]
failing = 0
for a in articles:
    issues = editorial.check_article(a, catalogue, today)
    slug = a.get("slug")
    if slug in slugs:
        issues.append(("error", f"slug also used by {slugs[slug]}"))
    slugs[slug] = a.get("_file")
    live = editorial.is_live(a, today)
    state = "LIVE" if live else a.get("status", "?")
    lines.append(f"## {a.get('_file')} [{state}]")
    if not issues:
        lines.append("- OK")
    for level, msg in issues:
        lines.append(f"- {level.upper()}: {msg}")
    if a.get("status") == "published" and issues:
        failing += 1
    lines.append("")
report = "\n".join(lines)
print(report)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as fh:
        fh.write(report + "\n")
sys.exit(1 if failing else 0)
