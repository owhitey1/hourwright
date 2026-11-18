#!/usr/bin/env python3
"""Ask Grok (xAI API) for one editorial submission or a visitor-experience check.

Grok gets the operating instruction (ops/GROK_SYSTEM_PROMPT.md), the editorial
standards, the in-stock catalogue and the list of published articles, and may
use xAI's web search tool for research. Its reply is treated as untrusted text:
it is written to a file for validation and filed as a GitHub issue by the
workflow. Nothing here can change code or publish.

Usage: grok_writer.py KIND OUT_DIR   (KIND: watch-of-the-week | news | guide | visitor-check)
Needs XAI_API_KEY. With GROK_DRY_RUN=1, uses a canned reply and makes no API call.
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import editorial  # noqa: E402

API = "https://api.x.ai/v1"
CONFIG = json.loads((ROOT / "config.json").read_text())
MODEL = os.environ.get("GROK_MODEL") or CONFIG.get("grok", {}).get("model", "grok-4.7")
PRICE_IN, PRICE_OUT = 2.0, 6.0  # USD per million tokens, xAI list price for the flagship (Nov 2026)

TASKS = {
    "watch-of-the-week": "Write next Monday's Watch of the Week. Choose one in-stock watch from the catalogue that has not been featured in the published articles listed. Set publish_after and week_of to next Monday's date ({monday}).",
    "news": "Write one Watch News & Features article on a genuine, recent (last 60 days) development from a watch brand in our catalogue, found with web search and confirmed in at least two independent sources, one of them the brand's own where possible. Link related catalogue watches only if they genuinely relate. Do not repeat a topic already published.",
    "guide": "Write one buying guide built from 3 to 6 in-stock catalogue watches that suit a clear buyer need (for example a budget band, a use, a size or a complication). Set price_ceiling where the guide has a budget. Do not duplicate a published guide.",
    "visitor-check": "Act as a visitor. Use web search/browsing to load https://hourwright.co.uk/, the journal, one brand page, one product page and the compare page. Report only concrete problems a visitor would hit (broken page, wrong or confusing information, missing disclosure, a buy button with no link). Never open or follow any affiliate link (awin1.com or a retailer 'View at' button): every visit counts as an artificial click. Reply with a JSON array only: [{\"title\": ..., \"url\": ..., \"observed\": ..., \"expected\": ...}]. Reply [] if you find nothing.",
}


def catalogue_lines(products):
    rows = [p for p in products if p.get("in_stock")]
    rows.sort(key=lambda p: (p["brand"], p["price"]))
    return "\n".join(f"{p['id']} | {p['brand']} | {p['name']} | ref {p.get('reference') or '-'} | £{p['price']:,.0f}" for p in rows)


def published_lines():
    out = []
    for a in editorial.load_articles():
        if a.get("_error"):
            continue
        out.append(f"{a.get('published')} | {a.get('type')} | {a.get('title')} | products: {', '.join(editorial.referenced_ids(a)) or '-'}")
    return "\n".join(out) or "(none)"


def build_messages(kind, today):
    monday = today + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)
    system = (ROOT / "ops" / "GROK_SYSTEM_PROMPT.md").read_text()
    standards = (ROOT / "ops" / "EDITORIAL_STANDARDS.md").read_text()
    products = list(editorial.load_catalogue(ROOT / "data" / "products.json").values())
    user = f"""Today is {today.isoformat()}.

TASK: {TASKS[kind].format(monday=monday.isoformat())}

OUTPUT: {'a JSON array only.' if kind == 'visitor-check' else 'exactly one article file inside a single ```markdown fenced block (front matter first, status: review, published: ' + (monday if kind == 'watch-of-the-week' else today).isoformat() + '), then a heading "### Verification notes" listing each specification or fact, the source URL that confirms it, and anything you could not confirm. Nothing else.'}

EDITORIAL STANDARDS (follow exactly):
{standards}

PUBLISHED ARTICLES:
{published_lines()}

IN-STOCK CATALOGUE (id | brand | name | reference | current price). Use ids exactly as written:
{catalogue_lines(products)}
"""
    return system, user


def call(system, user):
    key = os.environ["XAI_API_KEY"]
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    attempts = [
        ("responses", {"model": MODEL, "input": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                       "tools": [{"type": "web_search"}], "max_output_tokens": 8000}),
        ("chat/completions", {"model": MODEL, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                              "max_tokens": 8000}),
    ]
    last = None
    for path, payload in attempts:
        req = urllib.request.Request(f"{API}/{path}", data=json.dumps(payload).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                j = json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = f"{path}: HTTP {e.code} {e.read()[:300]!r}"
            print("xAI call failed,", last, file=sys.stderr)
            continue
        if path == "responses":
            text = j.get("output_text") or "".join(
                c.get("text", "") for o in j.get("output", []) if o.get("type") == "message" for c in o.get("content", []))
            u = j.get("usage", {})
            tin, tout = u.get("input_tokens", 0), u.get("output_tokens", 0)
            searched = True
        else:
            text = j["choices"][0]["message"]["content"]
            u = j.get("usage", {})
            tin, tout = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
            searched = False
        return text, {"endpoint": path, "model": j.get("model", MODEL), "input_tokens": tin, "output_tokens": tout,
                      "web_search": searched, "est_cost_usd": round(tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT, 4)}
    raise SystemExit(f"xAI API unavailable: {last}")


def main():
    kind, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    system, user = build_messages(kind, today)
    if os.environ.get("GROK_DRY_RUN") == "1":
        sample = next(f for f in sorted((ROOT / "content" / "editorial").glob("*.md")) if "wotw" in f.name)
        text = "```markdown\n" + sample.read_text().replace("status: published", "status: review") + "```\n\n### Verification notes\n\nDry run: no API call was made."
        if kind == "visitor-check":
            text = "[]"
        usage = {"endpoint": "dry-run", "model": MODEL, "input_tokens": len(user) // 4, "output_tokens": 0, "web_search": False, "est_cost_usd": 0}
    else:
        text, usage = call(system, user)
    (out / "reply.txt").write_text(text)
    (out / "usage.json").write_text(json.dumps(usage))
    print(json.dumps(usage))


if __name__ == "__main__":
    main()
