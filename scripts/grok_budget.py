#!/usr/bin/env python3
"""Monthly spend guard for the Grok (xAI API) workflow.

Every run records its estimated cost as a comment on the "Grok API usage ledger"
issue. Before calling xAI, this script totals the current calendar month's
entries and exits 1 (skipping the run) if the configured cap would be reached.
The real hard stop is xAI prepaid credit with auto top-up off; this is a second
guard that also keeps a public, auditable record (costs only, no content).

Usage: grok_budget.py check            -> exit 0 to proceed, 1 to stop
       grok_budget.py record USAGE.json KIND
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = os.environ.get("GITHUB_REPOSITORY", "owhitey1/hourwright")
TITLE = "Grok API usage ledger"
CAP = float(json.loads((ROOT / "config.json").read_text())["grok"].get("monthly_cap_usd", 5.5))
PER_RUN_ALLOWANCE = 0.30  # conservative headroom for one run incl. search-tool fees


def gh(*args, payload=None):
    r = subprocess.run(["gh", "api", *args] + (["--input", "-"] if payload else []), text=True, capture_output=True,
                       input=json.dumps(payload) if payload else None)
    if r.returncode:
        raise SystemExit(f"GitHub API error: {r.stderr[:300]}")
    return json.loads(r.stdout or "null")


def ledger():
    for i in gh(f"repos/{REPO}/issues?state=open&labels=source:grok-api&per_page=100"):
        if i["title"] == TITLE:
            return i["number"]
    return gh(f"repos/{REPO}/issues", payload={
        "title": TITLE, "labels": ["source:grok-api", "type:ops", "agent:claude"],
        "body": "One comment per Grok API run with its estimated cost at xAI list price. "
                f"The workflow stops for the month when the total reaches ${CAP:.2f}. Do not close."})["number"]


def month_total(n):
    month = dt.date.today().strftime("%Y-%m")
    total = 0.0
    page = 1
    while True:
        comments = gh(f"repos/{REPO}/issues/{n}/comments?per_page=100&page={page}")
        for c in comments:
            m = re.search(r"cost_usd=([\d.]+)", c["body"])
            if m and c["created_at"].startswith(month):
                total += float(m.group(1))
        if len(comments) < 100:
            return total
        page += 1


def main():
    n = ledger()
    if sys.argv[1] == "check":
        total = month_total(n)
        print(f"Grok spend this month: ${total:.2f} of ${CAP:.2f} cap")
        if total + PER_RUN_ALLOWANCE > CAP:
            print("::warning::Monthly Grok budget reached; skipping this run.")
            sys.exit(1)
        return
    usage = json.loads(Path(sys.argv[2]).read_text())
    kind = sys.argv[3]
    est = usage.get("est_cost_usd", 0) or 0
    if usage.get("web_search"):
        est += 0.05  # allowance for search-tool fees not shown in token usage
    gh(f"repos/{REPO}/issues/{n}/comments", payload={"body":
       f"{dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC · {kind} · model {usage.get('model')} · "
       f"{usage.get('input_tokens')} in / {usage.get('output_tokens')} out · cost_usd={est:.4f}"})


if __name__ == "__main__":
    main()
