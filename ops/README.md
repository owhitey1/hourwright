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

- **Grok via the xAI API** (`.github/workflows/grok.yml`): Tuesday and Friday news, Wednesday guide, Thursday next Monday's Watch of the Week, Saturday visitor check. The workflow can read the repository and write issues only. It cannot push code, deploy, or read any other secret. It is **off until the `XAI_API_KEY` secret exists**. Cost at xAI list price is roughly 7–10 US cents per article.
- **Issue form** ("Editorial submission"): anyone with a GitHub account can submit, and `editorial-intake.yml` validates it automatically. This is a fallback; the API route needs nobody to copy anything.
- **Claude cloud publisher**: a scheduled Claude task that runs in Anthropic's cloud (Steve's computer can be off). It validates, fact-checks, publishes or blocks, and handles Grok's visitor-check findings.
- Only Claude commits to the repository. Rollback is reverting a commit; the next build redeploys.

## Task register

GitHub Issues at https://github.com/owhitey1/hourwright/issues. Anyone can read it.

- Labels: `agent:claude|grok|chatgpt|steve`; `status:backlog|in-progress|awaiting-verification|blocked` (closed = completed); `priority:high|medium|low`; `type:engineering|editorial|ops|verification`; `source:grok-api` for issues filed by the Grok workflow.
- Each issue records the task, owner, evidence, completion criteria and outcome. An issue is closed only with evidence.
- Hourwright only. Other projects stay out of this repository.

## What runs where (verified 17 November 2026)

| Job | Runs in | Needs Steve's computer? | Verified |
| --- | --- | --- | --- |
| Feed import, tests, editorial report, build, link check, launch gate, deploy, smoke test (`site.yml`, daily 05:17 UTC and on every commit) | GitHub Actions | No | Yes, passing |
| Uptime, redirects, 404, all affiliate links' structure, a sample's landing pages, published articles' products (`monitor.yml`, every 6 hours) | GitHub Actions | No | Yes, passing |
| HTTPS settings check, re-enable if dropped, HTTP→HTTPS redirect test (`https.yml`, daily) | GitHub Actions | No | Yes, passing |
| Lighthouse and axe audit (`audit.yml`, Mondays) | GitHub Actions | No | Yes |
| Editorial form validation (`editorial-intake.yml`) | GitHub Actions | No | Yes, tested |
| Grok drafts and visitor checks (`grok.yml`) | GitHub Actions + xAI API | No | Pipeline tested in dry-run; live calls need `XAI_API_KEY` |
| Awin programme approvals and click tracking yes/no (`awin.yml`) | GitHub Actions + Awin API | No | Built; needs `AWIN_API_TOKEN` |
| Editorial fact-check and publishing; visitor-check triage | Claude scheduled task, cloud | No | Test runs succeeded |
| Awin status from the website (until the API token exists) | Claude scheduled task on SwiftyPlod, 11:43 London | **Yes**: computer on, desktop app open, Awin signed in | Runs; Awin sign-in often expires |
| Dependency updates | Dependabot, monthly | No | Yes; reviewed and applied by Claude |

**Failure alerts:** GitHub emails the repository owner (owhitey1) when a scheduled workflow fails. The Claude tasks send a phone notification when something needs Steve.

## Independent verification

- No agent certifies its own work.
- Claude checks Grok's articles (structure, products, prices, stock, specifications against primary sources, sources, copyright red flags). This is factual and technical checking, not a legal review.
- Grok's visitor checks review Claude's work from the visitor's side.
- ChatGPT audits with `REVIEW_PACK.md`. It can read this repository and the live site; it cannot see Claude or Grok sessions.
- Disagreements are recorded on the issue with evidence and resolved before anyone relies on the disputed claim.

## Measuring results

Keep separate and never add together: search impressions and clicks (Search Console), sessions (Google Analytics, consenting visitors only), outbound affiliate clicks (Analytics event `affiliate_click`), Awin clicks and attributed sales (tagged `clickref=hourwright`), and confirmed payable commission. Baseline: zero on 17 November 2026.
