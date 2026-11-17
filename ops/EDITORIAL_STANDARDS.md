# Editorial standards and article format

Applies to Watch of the Week, buying guides and news. Claude rejects submissions that do not meet them.

## Rules

1. **Researched, never hands-on.** Do not claim to have worn, tested or owned a watch. Every article carries a `basis` line saying how it was researched.
2. **Facts from primary sources.** Specifications come from the manufacturer's own site or press material first, then the authorised retailer. Note the source of each specification in the submission's verification notes.
3. **Prices and stock are never written into the text as current.** They come from the live feed through product cards. Say "under £3,000 when we published" rather than "costs £2,850".
4. **Original writing only.** No copied or closely paraphrased passages, no reproduced article structure, no third-party photographs. Short quotations only where necessary, under 15 words, attributed. Crediting a source is not permission to copy it.
5. **Images.** Product cards use retailer feed images supplied for affiliate promotion. Do not add other images unless Steve has confirmed a licence.
6. **Balanced.** Every featured watch gets reasons to consider it and things to weigh up. No "best" rankings without evidence, no urgency, no fabricated reviews.
7. **Links.** Link to the original publisher for news. Link products only with `{{product:id}}` tokens or the `products` list, never with raw retailer or Awin links.
8. **Relevance.** Only feature catalogue watches that genuinely fit the article. An article with no product link is fine.
9. **Goldsmiths pays no commission** on Rolex, Patek Philippe, Vacheron Constantin, Tudor, Grand Seiko, Jaeger-LeCoultre, TAG Heuer Connected, smart watches, or orders paid with interest-free or PayPal Credit. Those brands are filtered out of the catalogue. Never call a watch commission-eligible unless it has been checked.
10. **No paid promotion of discounts.** Never advertise percentage discounts or voucher codes (Goldsmiths and Beaverbrooks terms).

## Choosing a Watch of the Week

Prefer watches that are in stock with a good image and full retailer data, fit something people search for (dive, chronograph, under £3,000 and so on), have a story or design point worth explaining, and suit a buyer at Hourwright's price level. Never choose by price or commission alone. One product per feature.

## Finding products

The live catalogue is public at https://hourwright.co.uk/data/products.json (one record per watch: `id`, `brand`, `name`, `price`, `in_stock`, `reference`, `slug`). Use the `id` exactly as shown, for example `goldsmiths-41297899165`. The product page is `https://hourwright.co.uk/watches/<slug>.html`.

## File format

Save as `content/editorial/YYYY-MM-DD-short-name.md`:

```markdown
---
title: "Watch of the Week: Brand Model"
slug: watch-of-the-week-brand-model          # lowercase words and hyphens, unique
type: watch-of-the-week                      # watch-of-the-week | guide | news
status: approved                             # draft | review | approved | published (Claude sets published)
published: 2026-11-24                        # date shown on the article
publish_after: 2026-11-24                    # optional: goes live on the first daily build on or after this date
updated:                                     # optional: date of a material revision
week_of: 2026-11-23                          # Watch of the Week only
author: Hourwright
description: "One or two sentences used as the summary and meta description."
basis: "Researched from the manufacturer's published specifications and the retailer's listing. We have not handled this watch."
products: [goldsmiths-41297899165]           # catalogue ids; Watch of the Week takes exactly one
price_ceiling: 3000                          # optional: flags picks whose price rises above it
image_credit: "Product image supplied by Goldsmiths through its Awin product feed."
sources:
  - title: "Page title"
    url: "https://manufacturer.example/page"
    publisher: "Manufacturer"
---
Article text in Markdown. Place a live product card anywhere with:

{{product:goldsmiths-41297899165}}
```

## What happens automatically

- If a featured watch leaves the catalogue, goes out of stock or rises above `price_ceiling`, its buy button is replaced with a note, the home-page Watch of the Week hides itself, and the six-hourly monitor fails and emails the owner. Someone then updates the article.
- Drafts, reviews and approved articles are never published until Claude sets `status: published`.
