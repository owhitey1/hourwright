# Black Friday corrective actions (27 Nov 2026)

## 1. Pinterest link block
- Symptom: since 27 Nov 06:53, CREATE_PIN returns 429 "We blocked this link because it may lead to spam" for every hourwright.co.uk URL (journal page, offers page, with and without UTM). 7 pins published 20-26 Nov; 0 impressions in 7 days.
- Daily Pinterest scheduled task: DISABLED 27 Nov (re-enable after the block is lifted).
- Checked: Google Safe Browsing shows no data for hourwright.co.uk (not flagged). Outbound retailer links all carry rel="sponsored nofollow". No pin links directly to Awin or a retailer.
- Likely causes (Pinterest does not say which): brand-new domain and account with zero engagement; one pin a day all pointing to one young domain; pages consisting mainly of outbound affiliate links (Pinterest's spam rules call out pages that mostly redirect to other sites).
- Appeal (owner, signed in to the Hourwright Pinterest account): https://help.pinterest.com/en/contact -> "Something's broken" / "My website is blocked" (wording varies). Text:

  > Hello. Our website hourwright.co.uk has been blocked from being saved as a link ("We blocked this link because it may lead to spam"). Hourwright is an independent UK site comparing new luxury watches from UK authorised retailers, with original buying guides (for example https://hourwright.co.uk/journal/five-longines-watches-under-3000.html), brand pages and price comparisons. The domain is claimed and verified on our Pinterest business profile "hourwright". We publish at most one original pin a day, with no automation beyond scheduling, no redirects, no cloaking and no link shorteners. Retailer links on our pages are clearly disclosed as affiliate links and marked sponsored. We believe the block is a false positive for a new domain and would be grateful if you could review it. Thank you.

## 2. Channels not dependent on new social accounts
| Channel | Audience | Status / action |
|---|---|---|
| Google organic | High intent (1,557 impressions, avg position 51) | Live; IndexNow pings Bing on every deploy (automatic). Lever: rank Black Friday/brand pages; slow. |
| Awin Opportunity Marketplace | Retailers wanting placements | Live (listing 59352). Copy correction pending Awin sign-in. |
| More Awin retailers (stock = more pages that rank) | - | 5 applications prepared (below). |
| Deal communities (HotUKDeals) | Purchase-ready UK Black Friday buyers | Not used: their rules bar self-promotion and swap in their own links, so it earns nothing and risks a ban. |
| Watch forums / Reddit | Enthusiasts | Not used: self-promotion banned; advertising slots are paid. |
| Newsletters / creators (sponsored) | Buyers | Paid; needs approval. Free editorial pitches in outreach/QUEUE.md need approval to send. |

## 3. hello@hourwright.co.uk
MX mx00/mx01.ionos.co.uk, SPF include:_spf-eu.ionos.com, DMARC p=none: correctly configured to receive mail. Per setup, it forwards to the owner's inbox. End-to-end delivery not tested (no tool can send from here).

## 4. Awin clicks vs Analytics clicks
- 25-26 Nov: Awin 26 clicks; Analytics 0 visitors and 0 retailer clicks (consenting visitors only).
- 26 clicks with no recorded visitor cannot all be people who declined cookies. Most likely automated: search and link-preview crawlers following outbound links (nofollow is a hint, not a block), security scanners. Our own workflows do not request Awin links (monitor and link checker are structure-only). The 181 earlier clicks are the known test clicks (#25).
- Verdict for reporting: treat Analytics retailer clicks as the conservative human count, Awin clicks as an upper bound; sales are the only hard number. Awin's UI click report (referrer / user agent) can confirm on next sign-in.

## 5. Reporting
Daily report now has "Targets vs actual" using the same windows as ops/TARGETS.md (from 25 Nov).

## 6. Social accounts: owner steps only
Profile kit: ops/social/SETUP.md (name, handles, bio, links, images approved).
1. YouTube: youtube.com/verify, phone code. Then tell Claude; Claude creates the Hourwright brand channel, uploads avatar/banner, about, links, Shorts.
2. Instagram: instagram.com/accounts/emailsignup, email hello@hourwright.co.uk, name Hourwright, username hourwright, your password + date of birth + email code. Then switch to Professional (Creator/Business) yourself only if asked for ID.
3. TikTok: tiktok.com/signup, email hello@hourwright.co.uk, username hourwright, password, DOB, code.
4. Facebook: sign in to your Facebook in the Claude app browser; Claude creates the Page "Hourwright" (category Shopping & retail) and links Instagram.
After each: Claude adds the account as an Awin Promotional Space, then posts the Black Friday ad with "Ad" disclosure and UTM link.

## 7. Awin applications ready (owner only ticks the terms box and clicks Join)
Order: Chisholm Hunter (16071), Pleasance and Harper (19109), House of Watches (24385), F.Hinds (1625), WOLF watch winders (92577, accessory, 5%).
Promotion: https://hourwright.co.uk. Message: ops/AWIN_COPY.md. Not applying: Chrono24 (pre-owned/grey marketplace).

## 8. Partnerships (verified addresses, 27 Nov)
- WOLF: on Awin (92577), apply there instead of emailing.
- Farer: enquiries@farer.com (contact page; only address listed).
- Christopher Ward: press@christopherward.co.uk (press page). Its FlexOffers affiliate programme is closed. Use press for an editorial/partnership enquiry.
- Rapport London: no public trade email found; sold via Jura, W Hamond, Mr Porter. Pursue via those retailers' affiliate programmes.
Drafts remain in hourwright-ops/outreach/QUEUE.md and need owner approval to send.

## Housekeeping
Monitor flagged an article referencing 2 Goldsmiths products no longer in the catalogue (buy buttons auto-suppressed; no broken links).
