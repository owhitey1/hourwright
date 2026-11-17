"""Editorial content for Hourwright: Watch of the Week, buying guides, news and features.

Articles live in content/editorial/*.md as YAML front matter plus Markdown.
Only articles with status "published" and a publish date on or before today are
built. Product references are catalogue ids; prices, stock and links always come
from the live feed at build time, never from the article text.
"""
import datetime as dt
import re
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent
EDITORIAL_DIR = ROOT / "content" / "editorial"
TYPES = {"watch-of-the-week": "Watch of the Week", "guide": "Buying guide", "news": "News & features"}
STATUSES = ("draft", "review", "approved", "published")
PRODUCT_TOKEN = re.compile(r"\{\{\s*product:([a-z0-9-]+)\s*\}\}")
REQUIRED = ("title", "slug", "type", "status", "description", "published", "basis")


def load_articles():
    out = []
    for f in sorted(EDITORIAL_DIR.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            out.append({"_file": f.name, "_error": "missing front matter"})
            continue
        _, head, body = text.split("---\n", 2)
        meta = yaml.safe_load(head) or {}
        meta["_file"] = f.name
        meta["_body"] = body
        for k in ("published", "updated", "publish_after", "week_of"):
            if isinstance(meta.get(k), str):
                meta[k] = dt.date.fromisoformat(meta[k])
        out.append(meta)
    return out


def referenced_ids(a):
    ids = list(a.get("products") or [])
    ids += [m for m in PRODUCT_TOKEN.findall(a.get("_body", "")) if m not in ids]
    return ids


def is_live(a, today):
    if a.get("_error") or a.get("status") != "published":
        return False
    start = a.get("publish_after") or a.get("published")
    return isinstance(start, dt.date) and start <= today


def check_article(a, catalogue, today):
    """Return a list of (level, message). level is 'error' (blocks publishing) or 'flag' (needs review)."""
    issues = []
    if a.get("_error"):
        return [("error", a["_error"])]
    for k in REQUIRED:
        if not a.get(k):
            issues.append(("error", f"missing field: {k}"))
    if a.get("type") not in TYPES:
        issues.append(("error", f"unknown type: {a.get('type')}"))
    if a.get("status") not in STATUSES:
        issues.append(("error", f"unknown status: {a.get('status')}"))
    if a.get("slug") and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(a["slug"])):
        issues.append(("error", "slug must be lowercase words joined by hyphens"))
    if a.get("type") == "watch-of-the-week" and len(a.get("products") or []) != 1:
        issues.append(("error", "Watch of the Week needs exactly one product"))
    if a.get("type") == "news" and not a.get("sources"):
        issues.append(("error", "news needs at least one source"))
    for s in a.get("sources") or []:
        if not str(s.get("url", "")).startswith("https://"):
            issues.append(("error", f"source without an https URL: {s.get('title')}"))
    if re.search(r"\b(I|we) (tested|wore|tried|owned)\b|hands-on", a.get("_body", ""), re.I):
        issues.append(("flag", "wording suggests hands-on testing; Hourwright articles are researched, not hands-on"))
    ceiling = a.get("price_ceiling")
    for pid in referenced_ids(a):
        p = catalogue.get(pid)
        if not p:
            issues.append(("flag", f"product {pid} is no longer in the catalogue: buy button suppressed"))
            continue
        if p.get("in_stock") is False:
            issues.append(("flag", f"product {pid} is out of stock: buy button suppressed"))
        if ceiling and p["price"] > ceiling:
            issues.append(("flag", f"product {pid} now costs £{p['price']:,.0f}, above the £{ceiling:,} ceiling"))
    return issues


def render_body(a, product_html):
    body = PRODUCT_TOKEN.sub(lambda m: f"\n\n<!--P:{m.group(1)}-->\n\n", a["_body"])
    html = markdown.markdown(body, extensions=["tables"])
    html = html.replace("<table>", '<div class="scroll"><table>').replace("</table>", "</table></div>")
    return re.sub(r"<p><!--P:([a-z0-9-]+)--></p>|<!--P:([a-z0-9-]+)-->",
                  lambda m: product_html(m.group(1) or m.group(2)), html)
