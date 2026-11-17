#!/usr/bin/env python3
"""Daily Awin check through Awin's Publisher API (no browser sign-in needed).

Reports which watch programmes are joined or pending, and whether Awin has
recorded any Hourwright clicks in the last 7 days, as yes/no only. The
repository and its Actions logs are public, so no click counts, sales or
commission figures are ever printed. Opens a GitHub issue when a pending
programme is approved.

Needs AWIN_API_TOKEN (Awin > Account > API credentials). Exit 0 when the
secret is missing, so the workflow stays quiet until it is connected.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

PUB = "3102076"
WATCH = {"2174": "Goldsmiths", "5856": "Beaverbrooks", "7153": "Jura Watches", "16071": "Chisholm Hunter"}
TOKEN = os.environ.get("AWIN_API_TOKEN")


def get(path):
    req = urllib.request.Request(f"https://api.awin.com{path}", headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main():
    if not TOKEN:
        print("::notice::AWIN_API_TOKEN not set; Awin API check is off.")
        return 0
    status = {}
    for rel in ("joined", "pending", "rejected"):
        try:
            for p in get(f"/publishers/{PUB}/programmes?relationship={rel}"):
                pid = str(p.get("id"))
                if pid in WATCH:
                    status[pid] = rel
        except urllib.error.HTTPError as e:
            print(f"::error::Awin API {rel}: HTTP {e.code}")
            return 1
    lines = ["## Awin programmes", ""] + [f"- {name}: {status.get(pid, 'not joined')}" for pid, name in WATCH.items()]
    end = dt.date.today()
    try:
        rows = get(f"/publishers/{PUB}/reports/advertiser?startDate={end - dt.timedelta(days=7)}&endDate={end}"
                   f"&region=GB&timezone=Europe/London")
        clicks = any((r.get("clicks") or 0) > 0 for r in rows if str(r.get("advertiserId")) in WATCH)
        lines += ["", f"- Awin recorded Hourwright clicks in the last 7 days: {'yes' if clicks else 'no'}"]
    except urllib.error.HTTPError as e:
        lines += ["", f"- Click report unavailable (HTTP {e.code})"]
    report = "\n".join(lines)
    print(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(report + "\n")
    # Approved programme without a feed yet: open one issue for it.
    repo = os.environ.get("GITHUB_REPOSITORY")
    if repo:
        cfg = json.load(open("config.json"))
        live = {r.get("name") for r in cfg["retailers"] if r.get("status") == "live"}
        for pid, name in WATCH.items():
            if status.get(pid) == "joined" and name not in live:
                title = f"{name} approved on Awin: connect its product feed"
                existing = subprocess.run(["gh", "api", f"repos/{repo}/issues?state=open&per_page=100", "--jq", ".[].title"],
                                          capture_output=True, text=True).stdout.splitlines()
                if title not in existing:
                    body = (f"Awin shows Hourwright as joined to {name} (advertiser {pid}).\n\n"
                            "Steve: Awin > Toolbox > Create-a-Feed, choose this advertiser, CSV + gzip, copy the feed URL, and save it "
                            f"in GitHub > Settings > Secrets and variables > Actions as `AWIN_FEED_URL_{name.upper().replace(' ', '_')}`. "
                            "Claude then connects it.")
                    subprocess.run(["gh", "api", f"repos/{repo}/issues", "--input", "-"], text=True,
                                   input=json.dumps({"title": title, "body": body,
                                                     "labels": ["agent:steve", "type:ops", "status:backlog", "priority:high"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
