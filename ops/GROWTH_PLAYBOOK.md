# Organic growth playbook (18 Nov 2026)

Purpose: apply what has worked for eight growth-led businesses to Hourwright, keep what fits a small UK luxury-watch affiliate site, and track it in issue #26. **Documented** means stated by the company or a reputable report; **claimed** means third-party marketing write-ups whose figures conflict or cannot be checked.

## The eight models, judged for Hourwright

| Company | Principle | Evidence | Fit for Hourwright | Verdict |
| --- | --- | --- | --- | --- |
| Wise | Pages and tools that answer one exact high-intent query (currency pairs, fees) | Approach documented by many write-ups; traffic figures are claimed and conflict (16M to 90M monthly visits in different sources) | High: exact model-vs-model and budget questions, from the live catalogue | **Selected (1)** |
| Wirecutter | Rigorous, transparent recommendations with reasons and trade-offs, funded by affiliate links | Business model documented (NYT-owned; affiliate-funded) | High: our "consider" notes, sources, basis line and independent fact-check do this without claiming hands-on testing | **Selected (2)** |
| NerdWallet | Search-led education joined to comparison tools and a clear route to a provider | Model documented in its public filings; specifics not checked here | High: guides → finder/compare → retailer | **Selected (3)** |
| HubSpot | Topic clusters: pillar page plus linked subtopics | Widely documented method | High and cheap: collections, brands, guides and Journal now link both ways | **Selected (4)** |
| Ahrefs | Free tools that solve a real problem and attract the right visitors | Approach documented by Ahrefs itself | Medium-high: a watch finder built only on data we actually hold | **Selected (5)** |
| The Points Guy | Specialist, seasonal, commercially relevant editorial and a repeat audience | Model widely reported | Medium: seasonal guides yes; repeat audience needs email, which is not connected | Partly (seasonal) |
| Canva | Shareable, useful visual resources | Widely reported | Medium: Pinterest pins prepared; needs a Hourwright account | Prepared |
| Glossier | Community-led recommendations | Widely reported | Low for now: no community of our own, and most watch forums restrict commercial links | Deferred |

## The five tactics and what was done

1. **Exact-intent pages (Wise).** Done: HydroConquest vs Aquis Date; Christmas for her and for him; dive watches under £5,000 drafted (issue #27, for independent verification on 19 Nov). Next: Chanel J12 sizes (B7), GMT under £5,000 (B4).
2. **Trustworthy recommendations (Wirecutter).** Every guide: comparison table from maker specs, reasons and "consider" points per watch, sources, a basis line, no hands-on claims, independent fact-check before publishing.
3. **Education joined to tools (NerdWallet).** Done: watch finder at /watch-finder/ (budget, style, case size, brand); finder links to the right guide; home page leads with the finder; compare table shows case size instead of an always-empty colour row.
4. **Topic clusters (HubSpot).** Done: dive cluster = dive collection ↔ HydroConquest vs Aquis ↔ dive guide (pending) ↔ Legend Diver ↔ Longines and Oris brand pages; gift cluster = for her ↔ for him ↔ gift guide ↔ men's and ladies' collections.
5. **A useful free tool (Ahrefs).** The finder uses only what each retailer's listing states (price, and size and style from the product name). Watches with no stated size are excluded when a size is chosen. No invented specifications.

## Product pages: keep them out of the index (decision)

Product pages carry the retailer's own description and the same price and image as Goldsmiths' page, so each is a near-copy of a page Google already has. Indexing 743 of them risks the site being judged thin. Pages with real original content (guides, comparisons, collections, brands, the finder) are indexed instead and link to the products. Revisit when Search Console shows impressions for specific models: a product page could be indexed if it gains original content, such as a short Hourwright note with verified specs. Until then, no change.

## Distribution

| Channel | State | What it needs |
| --- | --- | --- |
| Google | Indexable pages and sitemap correct; IndexNow does not cover Google | Steve connects Search Console to Claude so results can be measured |
| Bing and IndexNow engines | Active, 83 URLs accepted 18 Nov; new pages sent on each deploy | Nothing |
| Pinterest | 9 original pins and copy ready (`ops/pinterest/`) | A Hourwright business profile (not Chrome & Coast Prints), connected to Claude |
| Instagram | Same pin artwork works as 4:5 posts; no account | Not recommended yet: organic reach for a new account without photography rights is low. Revisit after Pinterest |
| Facebook | No page; group posting with affiliate links is usually against group rules | Not recommended now |
| Watch forums and Reddit | No posting | Steve may take part personally, with disclosure, where rules allow |
| Editorial referrals | The finder and the comparison tables are the linkable assets | No bulk outreach. Later, cite them where genuinely relevant |

## Paid social (Meta) feasibility: not now

- **Policy.** Meta requires the landing page to match the ad and to work; affiliate landing pages with original content are allowed in principle (Meta Advertising Standards). The retailer's own Awin terms decide whether paid social is allowed at all, and brand-name bidding usually is not. Goldsmiths' terms must be read in Awin before any test (Awin was signed out on 18 Nov).
- **Economics.** Revenue per click = conversion rate × average order × commission rate. Goldsmiths' rate is shown in Awin, not checked here. With illustrative numbers only (1% of clicks buy, £2,500 order, 3% commission), a retailer click is worth about 75p, and a Meta ad click must lead to more than one retailer click to pay. Luxury watches have long consideration and low conversion, so small daily budgets give too few sales to learn from.
- **Evidence that would justify a £3–£5 a day test.** (1) Awin confirms paid social is permitted; (2) at least one tracked organic sale, so the conversion rate is real; (3) analytics shows at least 10% of guide visitors click through to a retailer; (4) a landing page (a gift guide) that already converts organic visitors.

## Measuring it

Issue #26 holds the weekly figures. Missing access: Search Console and Analytics (no connector connected), Awin (signed out; no API token). Finder use is recorded as a `finder_search` event in Analytics, for visitors who accept cookies.
