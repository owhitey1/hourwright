#!/usr/bin/env python3
"""Hourwright daily report: site health, publishing, Awin, Search Console, Analytics.

Designed to run in the PRIVATE repository owhitey1/hourwright-ops (its workflow
checks out this public repository for the code). Figures are written only to
a private issue there. Never run it with real credentials in a public repository:
the output contains earnings.

Each source is optional and is skipped with a note when its credentials are absent:
  AWIN_API_TOKEN        Awin Publisher API (read only)
  GOOGLE_SA_JSON        Google service-account key with read access to Search
                        Console (property sc-domain:hourwright.co.uk) and GA4
  GA4_PROPERTY_ID       GA4 property id (numeric)

Usage: daily_report.py OUT.md      (writes the report; exit 0 always unless --strict)
       daily_report.py OUT.md --strict   (exit 1 if a monitored check failed)
No affiliate link is ever requested.
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

PUB = "3102076"
SITE_REPO = "owhitey1/hourwright"
WATCH_PROGRAMMES = {"2174": "Goldsmiths", "5856": "Beaverbrooks", "16071": "Chisholm Hunter", "24383": "T. H. Baker"}
# Awin clicks recorded before the automated link checker was stopped (incident #25).
KNOWN_AUTOMATED = {"until": "2026-11-18T01:00:00+00:00", "goldsmiths_clicks": 181}
GSC_SITE = "sc-domain:hourwright.co.uk"
WORKFLOWS = {"site.yml": ("Build and deploy", 26), "monitor.yml": ("Monitor", 8), "https.yml": ("HTTPS", 26)}


def http_json(url, headers=None, data=None, method=None):
    req = urllib.request.Request(url, headers=headers or {}, data=data, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"null")


# ---------------------------------------------------------------- site health
def site_section(now):
    lines, problems = ["## Site and publishing"], []
    for wf, (label, max_age) in WORKFLOWS.items():
        try:
            runs = http_json(f"https://api.github.com/repos/{SITE_REPO}/actions/workflows/{wf}/runs?per_page=10",
                             {"Accept": "application/vnd.github+json"})["workflow_runs"]
        except Exception as e:  # noqa: BLE001
            lines.append(f"- {label}: could not read ({e.__class__.__name__})")
            continue
        done = [r for r in runs if r["status"] == "completed"]
        last = done[0] if done else None
        ok = next((r for r in done if r["conclusion"] == "success"), None)
        if not last:
            lines.append(f"- {label}: no completed runs")
            problems.append(label)
            continue
        age = (now - dt.datetime.fromisoformat(ok["updated_at"].replace("Z", "+00:00"))).total_seconds() / 3600 if ok else None
        status = "OK" if last["conclusion"] == "success" else f"FAILED ({last['conclusion']})"
        stale = age is None or age > max_age
        lines.append(f"- {label}: last run {status}; last success {age:.0f} h ago" if age is not None else f"- {label}: last run {status}; no success")
        if last["conclusion"] != "success" or stale:
            problems.append(label)
    try:
        issues = http_json(f"https://api.github.com/repos/{SITE_REPO}/issues?state=open&labels=type:editorial&per_page=50")
        waiting = [i for i in issues if any(l["name"] == "status:awaiting-verification" for l in i["labels"])]
        blocked = [i for i in issues if any(l["name"] == "status:blocked" for l in i["labels"])]
        lines.append(f"- Editorial queue: {len(waiting)} awaiting verification, {len(blocked)} blocked")
    except Exception:  # noqa: BLE001
        lines.append("- Editorial queue: could not read")
    return lines, problems


# ---------------------------------------------------------------------- Awin
def awin_section(today):
    token = os.environ.get("AWIN_API_TOKEN")
    if not token:
        return ["## Awin", "- Not connected (AWIN_API_TOKEN missing)."], []
    h = {"Authorization": f"Bearer {token}"}
    base = f"https://api.awin.com/publishers/{PUB}"
    lines, problems = ["## Awin"], []
    status = {}
    try:
        for rel in ("joined", "pending", "rejected", "suspended"):
            for p in http_json(f"{base}/programmes?relationship={rel}", h) or []:
                if str(p.get("id")) in WATCH_PROGRAMMES:
                    status[str(p["id"])] = rel
        lines.append("- Programmes: " + "; ".join(f"{n} {status.get(i, 'not joined')}" for i, n in WATCH_PROGRAMMES.items()))
        if status.get("2174") != "joined":
            problems.append("Goldsmiths not joined")
    except urllib.error.HTTPError as e:
        return lines + [f"- Awin API error HTTP {e.code} (token expired or revoked?)"], ["Awin API"]

    def report(start, end):
        q = urllib.parse.urlencode({"startDate": start.isoformat(), "endDate": end.isoformat(),
                                    "region": "GB", "timezone": "Europe/London"})
        rows = http_json(f"{base}/reports/advertiser?{q}", h) or []
        tot = {"clicks": 0, "sales": 0, "value": 0.0, "pending": 0.0, "approved": 0.0, "declined": 0.0}
        for r in rows:
            tot["clicks"] += r.get("clicks") or 0
            tot["sales"] += (r.get("pendingNo") or 0) + (r.get("confirmedNo") or 0)
            tot["value"] += (r.get("pendingValue") or 0) + (r.get("confirmedValue") or 0)
            tot["pending"] += r.get("pendingComm") or 0
            tot["approved"] += r.get("confirmedComm") or 0
            tot["declined"] += r.get("declinedComm") or 0
        return tot

    y = today - dt.timedelta(days=1)
    try:
        d1, mtd = report(y, y), report(today.replace(day=1), today)
        lines.append(f"- Yesterday: {d1['clicks']} clicks, {d1['sales']} sales, £{d1['value']:,.2f} sales value, "
                     f"£{d1['pending']:,.2f} commission pending")
        lines.append(f"- Month to date: {mtd['clicks']} clicks, {mtd['sales']} sales, £{mtd['value']:,.2f} sales value; "
                     f"commission £{mtd['pending']:,.2f} pending, £{mtd['approved']:,.2f} approved, £{mtd['declined']:,.2f} declined")
        if today.strftime("%Y-%m") == "2026-11":
            genuine = max(0, mtd["clicks"] - KNOWN_AUTOMATED["goldsmiths_clicks"])
            lines.append(f"- Clicks after excluding the 181 known automated test clicks (#25): {genuine}. "
                         "Not all of these are necessarily people; compare with Analytics affiliate_click below.")
    except urllib.error.HTTPError as e:
        lines.append(f"- Report unavailable (HTTP {e.code})")
    try:
        q = urllib.parse.urlencode({"startDate": f"{(today - dt.timedelta(days=30)).isoformat()}T00:00:00",
                                    "endDate": f"{today.isoformat()}T23:59:59", "timezone": "Europe/London"})
        tx = http_json(f"{base}/transactions/?{q}", h) or []
        by_page = {}
        for t in tx:
            refs = t.get("clickRefs") or {}
            key = f"{refs.get('clickRef') or 'untagged'}/{refs.get('clickRef2') or '-'}"
            by_page[key] = by_page.get(key, 0) + 1
        lines.append(f"- Transactions in the last 30 days: {len(tx)}" + (" by clickref/page: " + ", ".join(f"{k} {v}" for k, v in sorted(by_page.items())) if tx else ""))
    except urllib.error.HTTPError as e:
        lines.append(f"- Transactions unavailable (HTTP {e.code})")
    return lines, problems


# ------------------------------------------------------------ Google (SA key)
def google_token(scopes):
    raw = os.environ.get("GOOGLE_SA_JSON")
    if not raw:
        return None
    from google.oauth2 import service_account  # pip install google-auth
    from google.auth.transport.requests import Request
    creds = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=scopes)
    creds.refresh(Request())
    return creds.token


def gsc_section(today):
    token = google_token(["https://www.googleapis.com/auth/webmasters.readonly"])
    if not token:
        return ["## Search Console", "- Not connected (GOOGLE_SA_JSON missing)."], []
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    site = urllib.parse.quote(GSC_SITE, safe="")
    lines = ["## Search Console"]
    end = today - dt.timedelta(days=2)  # GSC data lags about two days
    start = end - dt.timedelta(days=6)
    try:
        body = json.dumps({"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": []}).encode()
        r = http_json(f"https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query", h, body, "POST")
        rows = r.get("rows") or []
        c = rows[0] if rows else {"clicks": 0, "impressions": 0, "position": 0}
        lines.append(f"- {start:%d %b}–{end:%d %b}: {c['clicks']:.0f} clicks, {c['impressions']:.0f} impressions"
                     + (f", average position {c['position']:.1f}" if rows else " (no data yet)"))
        body = json.dumps({"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": ["query"], "rowLimit": 5}).encode()
        top = http_json(f"https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query", h, body, "POST").get("rows") or []
        if top:
            lines.append("- Top queries: " + "; ".join(f"{t['keys'][0]} ({t['impressions']:.0f} impr, {t['clicks']:.0f} clicks)" for t in top))
        sm = http_json(f"https://www.googleapis.com/webmasters/v3/sites/{site}/sitemaps", h).get("sitemap") or []
        for s in sm:
            sub = sum(int(c.get("submitted", 0)) for c in s.get("contents", []))
            lines.append(f"- Sitemap {s['path']}: last read {s.get('lastDownloaded', '?')[:10]}, {sub} URLs, "
                         f"{s.get('errors', 0)} errors, {s.get('warnings', 0)} warnings")
    except urllib.error.HTTPError as e:
        lines.append(f"- Search Console API error HTTP {e.code}")
        return lines, ["Search Console"]
    return lines, []


def ga_section(today):
    prop = os.environ.get("GA4_PROPERTY_ID")
    token = google_token(["https://www.googleapis.com/auth/analytics.readonly"]) if prop else None
    if not token:
        return ["## Analytics (consenting visitors only)", "- Not connected (GOOGLE_SA_JSON or GA4_PROPERTY_ID missing)."], []
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    lines = ["## Analytics (consenting visitors only)"]
    try:
        body = json.dumps({"dateRanges": [{"startDate": "yesterday", "endDate": "yesterday"}, {"startDate": "7daysAgo", "endDate": "yesterday"}],
                           "metrics": [{"name": "sessions"}, {"name": "activeUsers"}]}).encode()
        r = http_json(f"https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport", h, body, "POST")
        vals = {row.get("dimensionValues", [{}])[-1].get("value", f"r{i}"): [m["value"] for m in row["metricValues"]]
                for i, row in enumerate(r.get("rows") or [])}
        lines.append(f"- Sessions / users: {json.dumps(vals) if vals else 'no data'}")
        body = json.dumps({"dateRanges": [{"startDate": "7daysAgo", "endDate": "yesterday"}],
                           "dimensions": [{"name": "eventName"}], "metrics": [{"name": "eventCount"}],
                           "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": "affiliate_click"}}}}).encode()
        r = http_json(f"https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport", h, body, "POST")
        n = sum(int(row["metricValues"][0]["value"]) for row in r.get("rows") or [])
        lines.append(f"- affiliate_click events, last 7 days: {n}")
    except urllib.error.HTTPError as e:
        lines.append(f"- Analytics API error HTTP {e.code}")
        return lines, ["Analytics"]
    return lines, []


def main():
    out = sys.argv[1]
    strict = "--strict" in sys.argv
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date()
    parts, problems = [f"# Hourwright daily report, {today:%a %d %b %Y}"], []
    for fn in (lambda: site_section(now), lambda: awin_section(today), lambda: gsc_section(today), lambda: ga_section(today)):
        try:
            lines, probs = fn()
        except Exception as e:  # noqa: BLE001  (one failing source never hides the others)
            lines, probs = [f"- Section failed: {e.__class__.__name__}"], ["report error"]
        parts += [""] + lines
        problems += probs
    parts += ["", "**Needs attention:** " + (", ".join(problems) if problems else "nothing")]
    open(out, "w").write("\n".join(parts) + "\n")
    print("\n".join(parts) if os.environ.get("HW_REPORT_PUBLIC_OK") else f"Report written to {out} ({len(problems)} items need attention)")
    sys.exit(1 if strict and problems else 0)


if __name__ == "__main__":
    main()
