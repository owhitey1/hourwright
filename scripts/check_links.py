#!/usr/bin/env python3
"""Fail if any internal link or asset in dist/ points at a file that does not exist."""
import os
import re
import sys
from pathlib import Path

dist = Path(os.environ.get("HW_DIST") or Path(__file__).resolve().parent.parent / "dist")
bad = []
for page in dist.rglob("*.html"):
    if page.name == "404.html":
        continue
    for ref in re.findall(r'(?:href|src)="([^"#]+)', page.read_text(encoding="utf-8")):
        if re.match(r"(https?:|mailto:|data:)", ref):
            continue
        if not (page.parent / ref).resolve().exists():
            bad.append(f"{page.relative_to(dist)} -> {ref}")
print(f"checked {len(list(dist.rglob('*.html')))} pages, {len(bad)} broken links")
for b in bad[:40]:
    print(" ", b)
sys.exit(1 if bad else 0)
