#!/usr/bin/env python3
"""Validate one editorial submission (a file, or a GitHub issue body from the
editorial form) against the live catalogue and the editorial standards.

Usage:
  validate_submission.py --file draft.md
  validate_submission.py --issue-body body.txt [--save content/editorial/NAME.md]

Prints a Markdown report. Exit 0 = no errors (flags may need a human eye),
1 = errors, 2 = no article found. Never publishes anything.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import editorial  # noqa: E402


def extract_article(text):
    """Find the article file in free text: a fenced block or bare front matter."""
    text = text.replace("\r\n", "\n")
    for m in re.finditer(r"```[a-zA-Z]*\n(.*?)\n```", text, re.S):
        if m.group(1).lstrip().startswith("---\n"):
            return m.group(1).strip() + "\n"
    m = re.search(r"(?m)^---\n.*?^---\n.*", text, re.S)
    if m:
        body = m.group(0)
        body = re.split(r"(?m)^### Verification notes", body)[0]
        return body.strip() + "\n"
    return None


def validate(text, catalogue, today):
    a = editorial.parse_text(text, "submission.md")
    issues = [("error", m) if ("no longer in the catalogue" in m or "out of stock" in m) else (lvl, m)
              for lvl, m in editorial.check_article(a, catalogue, today)]
    if not a.get("_error"):
        issues += editorial.submission_checks(a)
        existing = {x.get("slug"): x["_file"] for x in editorial.load_articles() if not x.get("_error")}
        if a.get("slug") in existing:
            issues.append(("flag", f"slug already used by {existing[a['slug']]} (fine only if this is a revision of it)"))
        for pid in editorial.referenced_ids(a):
            p = catalogue.get(pid)
            if p:
                issues.append(("info", f"{pid}: {p['brand']} {p['name']}, ref {p.get('reference') or '?'}, £{p['price']:,.0f}, "
                                       f"{'in stock' if p.get('in_stock') else 'out of stock'}"))
    return a, issues


def filename_for(a):
    d = a.get("publish_after") or a.get("published") or dt.date.today()
    return f"{d.isoformat()}-{a.get('slug', 'untitled')}.md"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--issue-body")
    ap.add_argument("--save", help="write the extracted article here if it has no errors")
    ap.add_argument("--json", help="write a machine-readable result here")
    args = ap.parse_args()
    raw = Path(args.file or args.issue_body).read_text(encoding="utf-8")
    text = raw if args.file else extract_article(raw)
    catalogue = editorial.load_catalogue(os.environ.get("HW_DATA") or ROOT / "data" / "products.json")
    today = dt.date.today()
    if not text:
        print("## Validation\n\n- ERROR: no article found. Paste the whole file, starting with the `---` front matter line.")
        result = {"ok": False, "errors": 1, "flags": 0}
        if args.json:
            Path(args.json).write_text(json.dumps(result))
        sys.exit(2)
    a, issues = validate(text, catalogue, today)
    errors = [m for lvl, m in issues if lvl == "error"]
    flags = [m for lvl, m in issues if lvl == "flag"]
    info = [m for lvl, m in issues if lvl == "info"]
    lines = ["## Automated validation", "",
             f"**{a.get('title', '(no title)')}** · type `{a.get('type')}` · status `{a.get('status')}` · file `{filename_for(a)}`", ""]
    lines += [f"- ❌ {m}" for m in errors] + [f"- ⚠️ {m}" for m in flags] + [f"- ℹ️ {m}" for m in info]
    if not errors and not flags:
        lines.append("- ✅ No problems found by the automated checks.")
    lines += ["", "Automated checks cover structure, products, prices, stock, links, quotation length and wording. "
              "Facts and originality are checked by Claude before publishing."]
    print("\n".join(lines))
    if args.save and not errors:
        Path(args.save).write_text(text, encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps({"ok": not errors, "errors": len(errors), "flags": len(flags),
                                               "filename": filename_for(a), "title": a.get("title"),
                                               "type": a.get("type")}))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
