# Hourwright operations

How Hourwright is run by three AI agents and Steve. Everything in this repository is public, including Actions logs. Never put credentials, feed URLs, earnings or personal data in files, issues or logs.

## Who does what

| Agent | Role | Owns | Must not |
| --- | --- | --- | --- |
| Claude | Technical Director | Code, repository, deployments, hosting, DNS and HTTPS, feeds, technical SEO, publishing, security, tests. Fact-checks and publishes all editorial content. | Publish anything that has not passed validation and a fact-check |
| Grok | Operations and Editorial Director | Editorial research and drafting, Watch of the Week, buying guides, news, affiliate and marketing research, visitor-experience checks | Change code, hosting, deployments or settings |
| ChatGPT | Independent audit | Evidence-based review of reports, claims and articles using `REVIEW_PACK.md`, the public repository and the live site | Certify its own work |
| Steve | Owner | Approvals, spending, accounts, credentials, legal commitments | |

## How work flows

```
Grok (xAI API, scheduled in GitHub Actions)   Steve or Grok chat (issue form, optional)
            \                                     /
             v                                   v
        GitHub issue, label type:editorial  ->  automated validation (comment + label)
                              |
                              v
     Claude cloud publisher (daily 10:13 London): fact-check against primary sources,
     correct or block, commit with status: published, close the issue with evidence
                              |
                              v
        Build and deploy (GitHub Actions) -> live site; 6-hourly monitor
```

- **Grok via the xAI API** (`.github/workflows/grok.yml`): Tuesday and Friday news, Wednesday guide, Thursday next Monday's Watch of the Week, Saturday visitor check. The workflow can read the repository and write issues only. It cannot push code, deploy, or read any other secret. It is **off until the `XAI_API_KEY` secret exists**. Grok must submit `status: review`; only Claude's verification advances an article. Cost at xAI list price is roughly 7–10 US cents per article plus any search fees. Two spending stops: xAI prepaid credit with auto top-up off and a $0 invoiced limit (requests are refused when credit runs out), and the workflow's own monthly cap of $5.50 (about £4.30) recorded in issue #22.
- **Issue form** ("Editorial submission"): anyone with a GitHub account can submit, and `editorial-intake.yml` validates it automatically. This is a fallback; the API route needs nobody to copy anything.
- **Claude cloud publisher**: a scheduled Claude task that runs in Anthropic's cloud (Steve's computer can be off). It validates, fact-checks, publishes or blocks, and handles Grok's visitor-check findings.
- Only Claude commits to the repository. Rollback is reverting a commit; the next build redeploys.

## Task register

GitHub Issues at https://github.com/owhitey1/hourwright/issues. Anyone can read it.

- Labels: `agent:claude|grok|chatgpt|steve`; `status:backlog|in-progress|awaiting-verification|blocked` (closed = completed); `priority:high|medium|low`; `type:engineering|editorial|ops|verification`; `source:grok-api` for issues filed by the Grok workflow.
- Each issue records the task, owner, evidence, completion criteria and outcome. An issue is closed only with evidence.
- Hourwright only. Other projects stay out of this repository.

## What runs where (audited 19 November 2026)

| Job | Runs in | Needs Steve's computer? | Status |
| --- | --- | --- | --- |
| Feed import, tests, build, deploy, smoke test (`site.yml`, daily and on every push) | GitHub Actions | No | Running |
| Uptime, redirects, 404, affiliate link structure (no links requested), published articles' products (`monitor.yml`, every 6 h) | GitHub Actions | No | Running |
| HTTPS settings and HTTP→HTTPS redirect (`https.yml`, daily) | GitHub Actions | No | Running |
| Lighthouse and axe (`audit.yml`, Mondays) | GitHub Actions | No | Running |
| Editorial form validation (`editorial-intake.yml`) | GitHub Actions | No | Running |
| Grok drafts (`grok.yml`) | GitHub Actions + xAI API | No | Off until `XAI_API_KEY` (#16); no cost while off |
| Editorial verification and publishing; restart of missed schedules | Claude scheduled task (cloud), 10:13 London | No | Running |
| **Daily report**: site health, publishing queue, Awin clicks/sales/commission and programme status, Search Console, Analytics (`scripts/daily_report.py`) | GitHub Actions in the **private** repo `owhitey1/hourwright-ops`, daily 07:41 UTC; report posted to a private issue and emailed by GitHub | No | **Live** for all four sections. Awin verified 19 Nov against the Awin dashboard. Search Console and Analytics connected 19 Nov with keyless Workload Identity Federation: service account `hourwright-reporting@zeta-range-431017-j1.iam.gserviceaccount.com` (no keys), Restricted user in Search Console, Viewer in GA4; Google issues tokens only to `daily-report.yml` on `main` of `owhitey1/hourwright-ops`. Figures verified against both Google interfaces on 19 Nov |
| Awin programme status from the Awin website | Claude scheduled task on SwiftyPlod | Yes | **Disabled 19 Nov**: replaced by the private daily report |
| Dependency updates | Dependabot | No | Running |

Awin, Search Console and Analytics figures are commercial data, so they are reported only in the private repository, never in this public one or its logs.

GitHub runs scheduled workflows on a best-effort basis and can delay or skip them; the cloud publisher restarts any core workflow that misses its window.

**Failure alerts:** GitHub emails owhitey1 when a workflow run fails (if Actions notifications are on in GitHub settings). Delivery cannot be confirmed from Claude's access. Test it any time: Actions > Monitor live site > Run workflow > tick "alert_test". The run fails on purpose and GitHub should email you. The Claude tasks send a phone notification when something needs Steve.

## Independent verification

- No agent certifies its own work.
- Claude checks Grok's articles (structure, products, prices, stock, specifications against primary sources, sources, copyright red flags). This is factual and technical checking, not a legal review.
- Grok's visitor checks review Claude's work from the visitor's side.
- ChatGPT audits with `REVIEW_PACK.md`. It can read this repository and the live site; it cannot see Claude or Grok sessions.
- Disagreements are recorded on the issue with evidence and resolved before anyone relies on the disputed claim.

## Affiliate links: never click them automatically

Awin records every request to an awin1.com link as a click. No workflow, script, scheduled task or agent may open affiliate links. Link health is checked from structure and feed freshness only (`scripts/check_affiliate_links.py`, guarded by tests). If a human ever needs to test a link, add `&clickref=hourwright-test` so it is separable in Awin's click-reference report. Incident record: issue #25 (181 automated clicks on 17 Nov, stopped 18 Nov).

Outbound clicks also carry `clickref2` with the page type (home, catalogue, product, journal, compare, collections, brands); Awin shows it in the transaction report, not the click report.

## Measuring results

Keep separate and never add together: search impressions and clicks (Search Console), sessions (Google Analytics, consenting visitors only), outbound affiliate clicks (Analytics event `affiliate_click`), Awin clicks and attributed sales (tagged `clickref=hourwright`), and confirmed payable commission. Baseline: zero on 17 November 2026. Weekly figures: issue #26. Acquisition plan: `ops/ACQUISITION.md`.
