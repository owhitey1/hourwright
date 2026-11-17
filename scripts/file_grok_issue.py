#!/usr/bin/env python3
"""File Grok's reply as GitHub issue(s) after automated validation.

Usage: file_grok_issue.py KIND OUT_DIR   (needs GH_TOKEN and GITHUB_REPOSITORY)
Articles: one issue labelled type:editorial, with the file, Grok's verification
notes, the validation report and the API usage. Visitor checks: one issue per
finding (at most 5), skipping titles that already have an open issue.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from validate_submission import extract_article, validate, filename_for  # noqa: E402

REPO = os.environ.get("GITHUB_REPOSITORY", "owhitey1/hourwright")


def gh(method, path, payload=None):
    cmd = ["gh", "api", "-X", method, f"repos/{REPO}/{path}"]
    r = subprocess.run(cmd + (["--input", "-"] if payload else []), input=json.dumps(payload) if payload else None,
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"GitHub API {path}: {r.stderr[:300]}")
    return json.loads(r.stdout or "null")


def summary(text):
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as fh:
            fh.write(text + "\n")
    print(text)


def file_article(kind, reply, usage):
    text = extract_article(reply)
    catalogue = {p["id"]: p for p in json.loads((ROOT / "data" / "products.json").read_text())["products"]}
    notes = reply.split("### Verification notes", 1)[1].strip() if "### Verification notes" in reply else "(none supplied)"
    if text:
        a, issues = validate(text, catalogue, dt.date.today())
        errors = [m for lvl, m in issues if lvl == "error"]
        flags = [m for lvl, m in issues if lvl == "flag"]
        report = "\n".join([f"- ❌ {m}" for m in errors] + [f"- ⚠️ {m}" for m in flags]
                           + [f"- ℹ️ {m}" for lvl, m in issues if lvl == "info"]) or "- ✅ No problems found by the automated checks."
        title = f"[Editorial] {a.get('title') or kind}"
        fname = filename_for(a)
    else:
        errors, flags, report = ["no article file found in Grok's reply"], [], "- ❌ No article file found in Grok's reply."
        title, fname, text = f"[Editorial] {kind}: no usable draft", "-", reply
    status = "status:blocked" if errors else "status:awaiting-verification"
    body = f"""Filed automatically from Grok (xAI API, model `{usage.get('model')}`, web search {'on' if usage.get('web_search') else 'off'}).

### Type

{kind}

### Article file

```markdown
{text.strip()}
```

### Verification notes

{notes}

### Automated validation

{report}

Proposed file: `content/editorial/{fname}`

**Next:** Claude fact-checks against primary sources and publishes, or replies with fixes. {'Errors must be fixed before publishing.' if errors else ''}

<sub>Usage: {usage.get('input_tokens')} input + {usage.get('output_tokens')} output tokens, about ${usage.get('est_cost_usd')} at list price.</sub>
"""
    issue = gh("POST", "issues", {"title": title[:200], "body": body,
                                  "labels": ["agent:grok", "type:editorial", status, "source:grok-api"]})
    summary(f"Filed issue #{issue['number']}: {title} ({status}; {len(errors)} errors, {len(flags)} flags)")


def file_visitor_check(reply, usage):
    m = re.search(r"\[.*\]", reply, re.S)
    try:
        findings = json.loads(m.group(0)) if m else []
    except json.JSONDecodeError:
        findings = [{"title": "Grok visitor check returned unreadable output", "url": "", "observed": reply[:1500], "expected": "A JSON list of findings"}]
    open_titles = {i["title"] for i in gh("GET", "issues?state=open&per_page=100")}
    filed = 0
    for f in findings[:5]:
        title = f"[Visitor check] {str(f.get('title', 'Finding'))[:150]}"
        if title in open_titles:
            continue
        body = (f"Reported by Grok's automated visitor check (model `{usage.get('model')}`). Not yet verified by Claude.\n\n"
                f"**Page:** {f.get('url', '')}\n\n**Observed:** {f.get('observed', '')}\n\n**Expected:** {f.get('expected', '')}\n")
        gh("POST", "issues", {"title": title, "body": body,
                              "labels": ["agent:claude", "type:ops", "status:awaiting-verification", "source:grok-api"]})
        filed += 1
    summary(f"Visitor check: {len(findings)} findings, {filed} new issues filed.")


def main():
    kind, out = sys.argv[1], Path(sys.argv[2])
    reply = (out / "reply.txt").read_text()
    usage = json.loads((out / "usage.json").read_text())
    if kind == "visitor-check":
        file_visitor_check(reply, usage)
    else:
        file_article(kind, reply, usage)


if __name__ == "__main__":
    main()
