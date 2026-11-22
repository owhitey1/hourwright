# Retailer onboarding: from approval to live listings

Use this when an affiliate programme approves Hourwright. Nothing here is live until the programme is approved, its terms are read and its feed passes every check below. Never add an unapproved retailer's links, and never say a watch is available from a retailer until its own feed shows it.

Pending applications (do not reapply), from the issue #9 register of 22 Nov 2026:

| Network | Programme | Feed type when approved |
| --- | --- | --- |
| Awin | Beaverbrooks (5856), Burrells, T. H. Baker (24383), Mappin & Webb (11017) | Awin Create-a-Feed, CSV + gzip, same columns as Goldsmiths |
| Rakuten Advertising | C.W. Sellors, TAG Heuer | Rakuten product catalogue file (see below) |

## 1. Steve's part (about five minutes)

1. Awin: Toolbox > Create-a-Feed, select the programme, CSV, gzip, include the columns listed at the top of `scripts/fetch_feed.py`, and copy the feed URL.
   Rakuten: in the publisher dashboard, open the programme's product feed (Links > Product Feeds, or the feed request the advertiser approves) and copy the download URL or FTP details.
2. Save it as a GitHub Actions secret in owhitey1/hourwright: `AWIN_FEED_URL_<RETAILER>` or `RAKUTEN_FEED_URL_<RETAILER>`. Never paste it into an issue or chat.

## 2. Claude's part

1. Read the programme terms: excluded brands, finance and voucher rules, brand bidding, cookie length. Put exclusions in the retailer's `exclude_brands` in `config.json`.
2. Add the retailer to `config.json` `retailers` with `status: "live"`, `feed_env`, `feed_merchant_names` and the approval date.
3. Non-Awin feeds: set `delimiter` (Rakuten catalogue files are usually pipe-delimited) and `column_map`, which maps the Awin column names the importer reads to this feed's own column names. `scripts/fetch_feed.py` applies it (`map_columns`), copying values unchanged.
4. Run the import, then check a sample of at least ten watches against the retailer's own product pages (price, reference, stock) by reading the retailer's page, never by following an affiliate link.
5. Update the link-structure checks before publishing: `scripts/check_affiliate_links.py` and the campaign audit currently expect Awin links (a=3102076). A Rakuten link has a different format; add its pattern for that retailer only, checked by structure, never by requesting it.
6. Report what the new range adds: brands Goldsmiths does not stock, and the same reference at two retailers (a real price comparison).

## Draft Rakuten column map (check against the first real file)

Rakuten's catalogue layout varies by advertiser and file version, so this map is a starting point, not a verified fact. Before the first import, read the file's header row and correct every entry. If a column does not exist, leave it out: missing values stay empty, they are never guessed.

```json
"delimiter": "|",
"column_map": {
  "aw_product_id": "Product ID",
  "product_name": "Product Name",
  "merchant_category": "Primary Category",
  "aw_deep_link": "Buy URL",
  "merchant_image_url": "Product Image URL",
  "description": "Long Product Description",
  "search_price": "Sale Price",
  "rrp_price": "Retail Price",
  "brand_name": "Brand",
  "mpn": "Manufacturer Part #",
  "in_stock": "Availability",
  "currency": "Currency",
  "ean": "UPC"
}
```

TAG Heuer is a brand selling its own watches, so its feed may include smartwatches (Connected) and straps; Goldsmiths' exclusion of TAG Heuer Connected suggests checking the TAG Heuer terms for the same. C.W. Sellors sells new and pre-owned watches: the importer already drops pre-owned and ex-display listings, and that must be checked on the first file.
