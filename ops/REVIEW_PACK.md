# Review pack for independent QA (ChatGPT)

Status as of 17 November 2026, written by Claude. Treat every item in "Claimed by Claude" as unverified until you have checked it yourself. You can read this public repository and the live site directly; you cannot see Claude's or Grok's sessions, Awin, Google Analytics or Search Console.

## 1. Facts you can verify yourself

| Claim | How to check |
| --- | --- |
| Site is live on HTTPS at hourwright.co.uk | Visit it; check the certificate |
| Catalogue of Goldsmiths watches from the Awin feed, with prices | /watches/ and /data/products.json |
| Product buttons go through Awin with `clickref=hourwright` | Inspect any "View at Goldsmiths" link |
| Pre-owned, ex-display and smart watches are excluded | Search /data/products.json for "pre-owned", "smart" |
| Product pages are noindex; collections, brands, guides and journal are in the sitemap | View source; /sitemap.xml |
| Analytics loads only after cookie consent | Open the site in a private window with dev tools; no googletagmanager request before accepting |
| Affiliate disclosure on every page | Footer and /disclosure.html |
| Journal: one Watch of the Week, one buying guide, one news article | /journal/ |
| Articles say they are researched, not hands-on, and link their sources | Each article's foot |
| Daily build, 6-hourly monitor | Actions tab: workflows "Build and deploy" and "Monitor" |

## 2. Claimed by Claude, not checkable from outside

- Awin account 3102076 (Worth Finding) is approved for Goldsmiths; Jura and Sellors are inactive; Beaverbrooks is pending.
- Google Search Console: sitemap submitted and accepted; home page indexed.
- GA4 property G-DZM0840BXK receives events; a test visit appeared in realtime.
- Three test products' prices matched the Goldsmiths site on 17 November.
- A test click reached Goldsmiths with Awin tracking parameters.

## 3. Assumptions

- Goldsmiths' excluded-brand list from its Awin programme terms is current.
- Retailer feed images may be used on product cards (supplied for affiliate promotion).
- The ICO data protection fee is likely payable (Tier 1, £52; £47 by direct debit), because the site uses analytics cookies to promote other businesses' goods. This is a self-assessment, not legal advice. Steve decides.

## 4. Known risks and limitations

- GitHub's "Enforce HTTPS" setting will not stay on (GitHub's domain check keeps returning "in progress"). The certificate works; a script redirects HTTP visitors. Retried daily.
- One retailer only. If Goldsmiths' feed or programme stops, the site loses all commercial links.
- The Awin sign-in in Claude's browser expires; the daily Claude check fails until Steve signs in again.
- The Claude daily task needs Steve's computer to be on. GitHub Actions jobs do not.
- No traffic yet. New domain; rankings will take weeks to months.
- Grok and ChatGPT cannot write to the task register directly.

## 5. What to review

1. The three articles in `content/editorial/`: factual accuracy against the cited sources, originality, balance, disclosure.
2. Whether `ops/EDITORIAL_STANDARDS.md` and `ops/GROK_HANDOVER.md` are clear and consistent.
3. Any claim in section 1 that does not hold.

Record findings with the "Verification" issue form (via Steve), one issue per finding, with the URL and evidence. Mark each as Confirmed, Disputed or Unable to verify.
