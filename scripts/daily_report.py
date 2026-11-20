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


def http_json(url, headers=None, data=None, method=None, timeout=60):
    req = urllib.request.Request(url, headers=headers or {}, data=data, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
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
    token = (os.environ.get("AWIN_API_TOKEN") or "").strip().strip('"').strip("'")
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not token:
        return ["## Awin", "- Not connected (AWIN_API_TOKEN missing)."], []
    h = {"Authorization": f"Bearer {token}"}
    base = f"https://api.awin.com/publishers/{PUB}"
    # Awin accepts an OAuth bearer token or an API key (x-api-key). Try each without ever printing the token.
    shape = f"{len(token)} chars"
    tried = []
    for mode, hdr in (("bearer", {"Authorization": f"Bearer {token}"}), ("x-api-key", {"x-api-key": token})):
        try:
            http_json(f"{base}/programmes?relationship=joined", hdr)
            h = hdr
            break
        except urllib.error.HTTPError as e:
            tried.append(f"{mode} HTTP {e.code}")
    else:
        return ["## Awin", f"- Awin rejected the credential ({'; '.join(tried)}; {shape}). "
                "Generate a fresh token in Awin > API Credentials and replace the AWIN_API_TOKEN secret."], ["Awin API"]
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


# --------------------------------------------------------------------- Google
# Auth: GOOGLE_ACCESS_TOKEN (short-lived, from keyless Workload Identity Federation
# in the private workflow) or, as a fallback, a service-account key in GOOGLE_SA_JSON.
def google_token(scopes):
    if os.environ.get("GOOGLE_ACCESS_TOKEN"):
        return os.environ["GOOGLE_ACCESS_TOKEN"]
    raw = os.environ.get("GOOGLE_SA_JSON")
    if not raw:
        return None
    from google.oauth2 import service_account  # pip install google-auth
    from google.auth.transport.requests import Request
    creds = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=scopes)
    creds.refresh(Request())
    return creds.token


def _gsc_query(h, site, body):
    return http_json(f"https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query", h,
                     json.dumps(body).encode(), "POST").get("rows") or []


def gsc_section(today):
    token = google_token(["https://www.googleapis.com/auth/webmasters.readonly"])
    if not token:
        return ["## Search Console", "- Not connected."], []
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    site = urllib.parse.quote(GSC_SITE, safe="")
    lines = ["## Search Console (organic Google search)"]
    try:
        # Google's data lags 2-3 days; find the latest day that has data in the last 10 days.
        days = _gsc_query(h, site, {"startDate": (today - dt.timedelta(days=10)).isoformat(), "endDate": today.isoformat(),
                                    "dimensions": ["date"], "dataState": "all"})
        latest = max((r["keys"][0] for r in days), default=None)
        end = dt.date.fromisoformat(latest) if latest else today - dt.timedelta(days=3)
        start = end - dt.timedelta(days=6)
        tot = _gsc_query(h, site, {"startDate": start.isoformat(), "endDate": end.isoformat(), "dataState": "all"})
        if tot:
            t = tot[0]
            lines.append(f"- {start:%d %b}–{end:%d %b} (latest available; Google lags 2–3 days): {t['clicks']:.0f} clicks, "
                         f"{t['impressions']:.0f} impressions, CTR {t['ctr']*100:.1f}%, average position {t['position']:.1f}")
        else:
            lines.append(f"- No search data recorded for {start:%d %b}–{end:%d %b} yet (new site; 0 impressions so far, or data still processing)")
        for dim, label in (("query", "Top queries"), ("page", "Top landing pages")):
            rows = _gsc_query(h, site, {"startDate": (end - dt.timedelta(days=27)).isoformat(), "endDate": end.isoformat(),
                                        "dimensions": [dim], "rowLimit": 5, "dataState": "all"})
            if rows:
                lines.append(f"- {label} (28 days): " + "; ".join(
                    f"{r['keys'][0].replace('https://hourwright.co.uk', '') or '/'} ({r['impressions']:.0f} impr, {r['clicks']:.0f} clicks)" for r in rows))
        sm = http_json(f"https://www.googleapis.com/webmasters/v3/sites/{site}/sitemaps", h).get("sitemap") or []
        for s_ in sm:
            sub = sum(int(c.get("submitted", 0)) for c in s_.get("contents", []))
            lines.append(f"- Sitemap: Google last read it {str(s_.get('lastDownloaded', '?'))[:10]}; {sub} URLs submitted; "
                         f"{s_.get('errors', 0)} errors, {s_.get('warnings', 0)} warnings")
    except urllib.error.HTTPError as e:
        lines.append(f"- Search Console API error HTTP {e.code} (check the service account is a user on the property)")
        return lines, ["Search Console"]
    except Exception as e:  # keep the section, flag it
        lines.append(f"- Search Console performance data failed: {type(e).__name__}")
        return lines, ["Search Console"]
    lines.append(_indexing_line(h))
    return lines, []


def _inspect(h, u):
    try:
        r = http_json("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect", h,
                      json.dumps({"inspectionUrl": u, "siteUrl": GSC_SITE}).encode(), "POST", timeout=25)
        return (r.get("inspectionResult", {}).get("indexStatusResult", {}) or {}).get("coverageState", "Unknown")
    except urllib.error.HTTPError as e:
        return f"inspection error {e.code}"
    except Exception as e:
        return f"inspection {type(e).__name__}"


def _indexing_line(h, budget_s=240):
    """Indexed vs submitted via the URL Inspection API (free; 2,000/day). Never fails the section."""
    import concurrent.futures as cf
    import time
    try:
        sm_xml = urllib.request.urlopen("https://hourwright.co.uk/sitemap.xml", timeout=30).read().decode()
    except Exception as e:
        return f"- Indexing: not checked (sitemap fetch failed: {type(e).__name__})"
    urls = [u.split("</loc>")[0] for u in sm_xml.split("<loc>")[1:]][:150]
    verdicts, deadline = {}, time.monotonic() + budget_s
    pool = cf.ThreadPoolExecutor(max_workers=6)
    futs = [pool.submit(_inspect, h, u) for u in urls]
    for f in futs:
        left = deadline - time.monotonic()
        try:
            st = f.result(timeout=max(left, 0.01))
        except cf.TimeoutError:
            st = "not checked (time limit)"
        verdicts[st] = verdicts.get(st, 0) + 1
    pool.shutdown(wait=False, cancel_futures=True)
    indexed = sum(v for k, v in verdicts.items() if "indexed" in k.lower() and "not" not in k.lower())
    return (f"- Indexing: {indexed} of {len(urls)} sitemap URLs indexed. Breakdown: "
            + "; ".join(f"{k} {v}" for k, v in sorted(verdicts.items(), key=lambda x: -x[1])))


def _ga_report(h, prop, body):
    return http_json(f"https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport", h,
                     json.dumps(body).encode(), "POST").get("rows") or []


def ga_section(today):
    prop = os.environ.get("GA4_PROPERTY_ID")
    token = google_token(["https://www.googleapis.com/auth/analytics.readonly"]) if prop else None
    if not token:
        return ["## Analytics (consenting visitors only)", "- Not connected."], []
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    lines = ["## Analytics (visitors who accepted cookies only; yesterday's figures can still change)"]
    try:
        for label, rng in (("Yesterday", {"startDate": "yesterday", "endDate": "yesterday"}),
                           ("Last 7 days", {"startDate": "7daysAgo", "endDate": "yesterday"})):
            r = _ga_report(h, prop, {"dateRanges": [rng], "metrics": [{"name": "activeUsers"}, {"name": "sessions"},
                                                                      {"name": "screenPageViews"}]})
            v = [m["value"] for m in r[0]["metricValues"]] if r else ["0", "0", "0"]
            ev = _ga_report(h, prop, {"dateRanges": [rng], "dimensions": [{"name": "eventName"}], "metrics": [{"name": "eventCount"}],
                                      "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": "affiliate_click"}}}})
            clicks = sum(int(x["metricValues"][0]["value"]) for x in ev)
            lines.append(f"- {label}: {v[0]} users, {v[1]} sessions, {v[2]} page views, {clicks} retailer clicks (affiliate_click)")
        src = _ga_report(h, prop, {"dateRanges": [{"startDate": "28daysAgo", "endDate": "yesterday"}],
                                   "dimensions": [{"name": "sessionDefaultChannelGroup"}], "metrics": [{"name": "sessions"}],
                                   "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}], "limit": 6})
        if src:
            lines.append("- Traffic sources (28 days): " + "; ".join(f"{x['dimensionValues'][0]['value']} {x['metricValues'][0]['value']}" for x in src))
        lp = _ga_report(h, prop, {"dateRanges": [{"startDate": "28daysAgo", "endDate": "yesterday"}],
                                  "dimensions": [{"name": "landingPage"}], "metrics": [{"name": "sessions"}],
                                  "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}], "limit": 5})
        if lp:
            lines.append("- Top landing pages (28 days): " + "; ".join(f"{x['dimensionValues'][0]['value']} {x['metricValues'][0]['value']}" for x in lp))
        bypage = _ga_report(h, prop, {"dateRanges": [{"startDate": "28daysAgo", "endDate": "yesterday"}],
                                      "dimensions": [{"name": "pagePath"}], "metrics": [{"name": "eventCount"}],
                                      "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": "affiliate_click"}}},
                                      "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}], "limit": 5})
        if bypage:
            lines.append("- Retailer clicks by page (28 days): " + "; ".join(f"{x['dimensionValues'][0]['value']} {x['metricValues'][0]['value']}" for x in bypage))
        # Actual website visits from Pinterest (any session whose source contains "pinterest": utm-tagged pins and organic referrals)
        pin_filter = {"filter": {"fieldName": "sessionSource", "stringFilter": {"matchType": "CONTAINS", "value": "pinterest", "caseSensitive": False}}}
        for label, rng in (("yesterday", {"startDate": "yesterday", "endDate": "yesterday"}),
                           ("last 7 days", {"startDate": "7daysAgo", "endDate": "yesterday"})):
            r = _ga_report(h, prop, {"dateRanges": [rng], "metrics": [{"name": "sessions"}, {"name": "activeUsers"}],
                                     "dimensionFilter": pin_filter})
            v = [m["value"] for m in r[0]["metricValues"]] if r else ["0", "0"]
            ev = _ga_report(h, prop, {"dateRanges": [rng], "metrics": [{"name": "eventCount"}],
                                      "dimensionFilter": {"andGroup": {"expressions": [pin_filter,
                                          {"filter": {"fieldName": "eventName", "stringFilter": {"value": "affiliate_click"}}}]}}})
            pc = ev[0]["metricValues"][0]["value"] if ev else "0"
            lines.append(f"- From Pinterest, {label}: {v[0]} sessions, {v[1]} users, {pc} retailer clicks")
    except urllib.error.HTTPError as e:
        lines.append(f"- Analytics API error HTTP {e.code} (check the service account has Viewer access to the property)")
        return lines, ["Analytics"]
    return lines, []


def pinterest_section(today):
    """Pinterest figures saved by the daily Hourwright pin task (Composio, Hourwright account only)."""
    path = os.environ.get("HW_PINTEREST_STATS")
    if not path or not os.path.exists(path):
        return ["## Pinterest (Hourwright profile)", "- No figures yet (the daily pin task saves them)."], []
    try:
        d = json.load(open(path))
    except Exception as e:
        return ["## Pinterest (Hourwright profile)", f"- Stats file unreadable: {type(e).__name__}"], ["Pinterest"]
    lines = ["## Pinterest (Hourwright profile; Pinterest's own figures, may lag 1-2 days)"]
    age = (today - dt.date.fromisoformat(d.get("saved", "1970-01-01"))).days
    for key, label in (("yesterday", "Yesterday"), ("last_7_days", "Last 7 days")):
        m = d.get(key) or {}
        lines.append(f"- {label}: {m.get('impressions', '?')} impressions, {m.get('outbound_clicks', '?')} outbound clicks, "
                     f"{m.get('saves', '?')} saves")
    lines.append(f"- Pins published: {d.get('pins_published', '?')}; last published: {d.get('last_pin', '-')}; next: {d.get('next_pin', '-')}")
    problems = []
    if age > 2:
        lines.append(f"- Stats are {age} days old: the daily pin task may not be running.")
        problems.append("Pinterest")
    return lines, problems


def main():
    out = sys.argv[1]
    strict = "--strict" in sys.argv
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date()
    parts, problems = [f"# Hourwright daily report, {today:%a %d %b %Y}"], []
    for fn in (lambda: site_section(now), lambda: awin_section(today), lambda: gsc_section(today), lambda: ga_section(today), lambda: pinterest_section(today)):
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
