# Hourwright operations

How Hourwright is run by three AI agents and Steve. Everything here is public, because the repository is public. Never put credentials, feed URLs, earnings or personal data in this folder or in issues.

## Who does what

| Agent | Role | Owns | Must not |
| --- | --- | --- | --- |
| Claude | Technical Director | Code, repository, deployments, hosting, DNS and HTTPS, feeds, technical SEO, publishing system, security, tests, engineering docs. Validates and publishes editorial submissions. | Publish editorial content that has not passed the checks below |
| Grok | Operations and Editorial Director | Research, editorial planning and drafting, Watch of the Week selection, source verification, marketing and affiliate research, commercial reporting, routine enquiries, raising technical requests | Change code, hosting or deployments |
| ChatGPT | Independent quality assurance | Reviews Claude's technical claims, Grok's factual and commercial claims, reports and disputes | Certify its own work |
| Steve | Owner | Approvals, spending, accounts, credentials, legal commitments | |

## Shared task register: GitHub Issues

The register is the Issues list at https://github.com/owhitey1/hourwright/issues.

- Anyone can read it without an account, so Grok and ChatGPT can always see the current state.
- Creating or updating issues needs a GitHub account. Claude has write access. Grok and ChatGPT do not have accounts on this repository, so they hand their submissions to Steve, who opens them with the issue forms (about a minute each), or to Claude in its chat with Steve.
- Labels: `agent:claude`, `agent:grok`, `agent:chatgpt`, `agent:steve`; `status:backlog`, `status:in-progress`, `status:awaiting-verification`, `status:blocked`; closed means completed; `priority:high|medium|low`; `type:engineering|editorial|ops|verification`.
- Each issue records the task, owner, priority, status, evidence, dependencies, verification needed, completion criteria and outcome.
- Hourwright only. Firwick and other projects are kept out of this repository.

## Publishing pipeline

1. Grok researches and writes an article in the format in `EDITORIAL_STANDARDS.md`.
2. Steve pastes it into the "Editorial submission" issue form, or passes it to Claude in chat.
3. Claude validates product ids, prices, stock, price ceilings, links, sources, disclosures and wording, runs `scripts/editorial_check.py`, and either publishes (commits the file with `status: published`) or replies on the issue with fixes.
4. The site rebuilds on every commit and every day at 05:17 UTC. An article with a future `publish_after` date goes live on the first build on or after that date.
5. Revisions are new commits. Rollback is reverting a commit; the next build redeploys.

Only Claude commits to the repository, so two agents cannot make conflicting changes at the same time.

## What runs on its own, and what does not

| Job | Where it runs | Needs |
| --- | --- | --- |
| Feed import, tests, editorial report, build, link check, launch gate, deploy, live smoke test | GitHub Actions, daily and on every commit | Nothing (cloud) |
| Uptime, redirects, 404, affiliate link sample, published-article product check | GitHub Actions, every 6 hours | Nothing (cloud). Failures email the repository owner |
| Dependency update proposals | Dependabot, monthly | Nothing (cloud). Claude reviews before merging |
| Hourwright daily Awin and site check | Claude scheduled task, 11:43 London | Steve's computer on and the Claude desktop app open; Awin and GitHub signed in in its browser |
| Editorial validation and publishing | Claude, on request | A Claude session with repository access |
| Awin approvals, commission data, account changes | Awin website | An active Awin sign-in; account changes need Steve |

Nothing in the last three rows is fully unattended.

## Independent verification

No agent certifies its own work. Checks are proportionate to risk:

- Claude checks Grok's articles for product ids, prices, stock, specifications against primary sources, links, disclosures and copyright red flags. This is a technical and factual check, not a legal review.
- Grok checks Claude's work from the visitor's side: live pages, navigation, product links and the purchase journey.
- ChatGPT reviews `REVIEW_PACK.md` and any issue labelled `type:verification`. It can read this public repository and the live site directly.
- Disagreements are recorded on the relevant issue with evidence and resolved before anyone relies on the disputed claim.

## Measuring results

Keep these separate and never add them together: search impressions and clicks (Google Search Console), sessions and page views (Google Analytics, only from visitors who accept cookies), outbound affiliate clicks (Analytics event `affiliate_click`), Awin clicks and attributed sales (Awin, tagged `clickref=hourwright`), and confirmed payable commission (Awin, after validation). The baseline is zero on 17 November 2026, the commercial launch date.
