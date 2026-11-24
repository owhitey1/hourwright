#!/usr/bin/env python3
"""Download Awin product feeds and write data/products.json.

Rules this script enforces:
  * Every price, link, image, stock flag and specification comes from the
    retailer's own Awin feed. Nothing is generated or estimated here.
  * If a feed looks broken (too few rows, or a sudden large drop), the
    previous good data is kept and the script exits non-zero.

Feed URLs are secrets (they contain your Awin API key). Supply each one in
the environment variable named by "feed_env" in config.json, for example
AWIN_FEED_URL_JURA. Create the URL in Awin: Toolbox > Create-a-Feed, format
CSV, gzip compression, and include at least these columns:
  aw_deep_link, product_name, aw_product_id, merchant_product_id,
  merchant_image_url, description, merchant_category, search_price,
  merchant_name, merchant_id, category_name, aw_image_url, currency,
  rrp_price, product_price_old, brand_name, in_stock, ean, mpn,
  model_number, colour, specifications, last_updated
"""
import csv
import datetime as dt
import gzip
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "products.json"


def slugify(text):
    text = re.sub(r"&", " and ", str(text).lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def to_price(value):
    """Return a float price, or None when the feed value is not a clean number."""
    if value is None:
        return None
    s = str(value).strip().replace(",", "").replace("£", "")
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        return None
    p = float(s)
    return p if p > 0 else None


def to_stock(value):
    s = str(value or "").strip().lower()
    if s in ("1", "yes", "true", "in stock", "instock", "y"):
        return True
    if s in ("0", "no", "false", "out of stock", "outofstock", "n"):
        return False
    return None  # feed did not say


def is_watch(row, feed_cfg):
    cats = " ".join(str(row.get(k, "")) for k in ("merchant_category", "category_name")).lower()
    name = str(row.get("product_name", "")).lower()
    if not any(w in cats or w in name for w in feed_cfg["watch_category_include"]):
        return False
    return not any(x in name for x in feed_cfg["name_exclude"])


def group_key(row):
    """Key that identifies the same model at different retailers."""
    ean = re.sub(r"\D", "", str(row.get("ean", "")))
    if len(ean) in (8, 12, 13, 14):
        return "ean:" + ean.lstrip("0")
    ref = str(row.get("mpn") or row.get("model_number") or "").strip()
    brand = str(row.get("brand_name", "")).strip()
    if ref and brand and len(ref) >= 5:
        return "ref:" + slugify(brand) + ":" + re.sub(r"[^a-z0-9]", "", ref.lower())
    return None


WATCH_TEXT = re.compile(r"\b(watch|watches|dial|movement|calibre|caliber|chronograph|water[- ]resistan\w*|bezel)\b", re.I)


def normalise_row(row, retailer, cfg):
    """Turn one feed row into a product dict, or None if it must be skipped."""
    feed_cfg = cfg["feed"]
    price = to_price(row.get("search_price"))
    link = str(row.get("aw_deep_link", "")).strip()
    name = str(row.get("product_name", "")).strip()
    brand = str(row.get("brand_name", "")).strip()
    pid = str(row.get("aw_product_id") or row.get("merchant_product_id") or "").strip()
    currency = str(row.get("currency", "")).strip().upper()
    if not (price and name and brand and pid):
        return None
    network = retailer.get("network", "awin")
    prefix = {"awin": "https://www.awin1.com/", "rakuten": "https://click.linksynergy.com/"}[network]
    if not link.startswith(prefix):
        return None  # only genuine network tracking links are ever published
    if currency != "GBP":
        return None
    if price < cfg["price_floor_gbp"]:
        return None
    if cfg.get("price_ceiling_gbp") and price > cfg["price_ceiling_gbp"]:
        return None
    if not is_watch(row, feed_cfg):
        return None
    if retailer.get("watch_text_required") and not WATCH_TEXT.search(
            " ".join(str(row.get(k, "")) for k in ("product_name", "description", "specifications"))):
        return None  # retailer files jewellery and watches in one category; keep only items described as watches
    if brand.lower() in [b.lower() for b in retailer.get("exclude_brands", [])]:
        return None  # retailer pays no commission on this brand
    if re.search(r"smart|connected", name, re.I):
        return None
    if re.search(r"pre-?owned|ex-?display|refurbished|second[ -]?hand|vintage", brand + " " + name, re.I):
        return None  # Hourwright lists new watches only
    if network == "awin" and "clickref=" not in link:
        link += "&clickref=hourwright"  # separates Hourwright clicks from other Worth Finding spaces in Awin reports
    was = to_price(row.get("rrp_price")) or to_price(row.get("product_price_old"))
    image = str(row.get("merchant_image_url") or row.get("aw_image_url") or "").strip()
    ref = str(row.get("mpn") or row.get("model_number") or "").strip()
    return {
        "id": f"{retailer['id']}-{pid}",
        "slug": slugify(f"{brand} {name}")[:90] + "-" + slugify(pid),
        "retailer": retailer["id"],
        "retailer_name": retailer["name"],
        "brand": brand,
        "name": name,
        "price": price,
        "was_price": was if was and was > price else None,
        "in_stock": to_stock(row.get("in_stock")),
        "link": link,
        "image": image if image.startswith("https://") else "",
        "description": str(row.get("description", "")).strip()[:1500],
        "reference": ref,
        "colour": str(row.get("colour", "")).strip(),
        "specifications": str(row.get("specifications", "")).strip()[:1500],
        "category": str(row.get("merchant_category") or row.get("category_name") or "").strip(),
        "group": group_key(row),
        "feed_updated": str(row.get("last_updated", "")).strip(),
    }


def parse_feed(raw_bytes, delimiter=","):
    if raw_bytes[:2] == b"\x1f\x8b":
        raw_bytes = gzip.decompress(raw_bytes)
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def map_columns(rows, column_map):
    """Rename a non-Awin feed's columns to the Awin names the rest of this script reads.

    column_map is {"<awin column>": "<column in this feed>"} from the retailer's config
    entry. Values are copied unchanged; a column missing from the feed stays empty."""
    if not column_map:
        return rows
    return [{**r, **{awin: r.get(src, "") for awin, src in column_map.items()}} for r in rows]


RAKUTEN_API = "https://api.linksynergy.com"


def rakuten_brand(name, brands):
    """Brand from the start of a Rakuten product name (Product Search has no brand field).
    Only known brands are accepted; anything else is skipped rather than guessed."""
    low = name.lower()
    best = ""
    for alias in brands:
        if low.startswith(alias + " ") and len(alias) > len(best):
            best = alias
    return brands[best] if best else ""


def rakuten_reference(text):
    """Manufacturer reference from the first sentence of a C.W. Sellors description,
    e.g. 'Maurice Lacroix Watch Aikon Automatic 39mm AI6007-SP012-130-1.' -> 'AI6007-SP012-130-1'."""
    first = str(text or "").split(". ")[0].strip().rstrip(".")
    token = first.split(" ")[-1] if first else ""
    if len(token) >= 5 and re.search(r"\d", token) and re.search(r"[A-Za-z]|[.\-/]", token) and not re.fullmatch(r"\d+mm", token, re.I):
        return token
    return ""


def rakuten_items_to_rows(xml_text, brands):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_text)
    rows = []
    for it in root.iter("item"):
        g = lambda tag: (it.findtext(tag) or "").strip()
        name = g("productname")
        price_el, sale_el = it.find("price"), it.find("saleprice")
        sale = (sale_el.text or "").strip() if sale_el is not None else ""
        retail = (price_el.text or "").strip() if price_el is not None else ""
        cur = (sale_el if sale_el is not None and sale else price_el)
        long_desc = (it.findtext("description/long") or it.findtext("description/short") or "").strip()
        rows.append({
            "product_name": name,
            "brand_name": rakuten_brand(name, brands),
            "aw_deep_link": g("linkurl"),
            "search_price": sale or retail,
            "rrp_price": retail,
            "currency": (cur.get("currency", "") if cur is not None else ""),
            "aw_product_id": g("sku") or g("linkid"),
            "merchant_image_url": g("imageurl"),
            "description": long_desc,
            "merchant_category": " / ".join(x for x in ((it.findtext("category/primary") or "").strip(),
                                                        (it.findtext("category/secondary") or "").strip()) if x),
            "ean": g("upccode"),
            "mpn": rakuten_reference(long_desc),
            "in_stock": "",  # Product Search does not report stock; left unknown, never guessed
        })
    return rows, int(root.findtext("TotalPages") or 0)


def fetch_rakuten(retailer, brands):
    """All of one advertiser's catalogue via the Rakuten Product Search API (XML, 100 per page)."""
    token_key = os.environ.get(retailer["feed_env"], "").strip()
    if not token_key:  # or build it from the developer-portal Client ID and Secret
        import base64
        cid, secret = os.environ.get("RAKUTEN_CLIENT_ID", "").strip(), os.environ.get("RAKUTEN_CLIENT_SECRET", "").strip()
        token_key = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    body = urllib.parse.urlencode({"scope": retailer["rakuten_sid"]}).encode()
    req = urllib.request.Request(RAKUTEN_API + "/token", body, method="POST", headers={
        "Authorization": "Bearer " + token_key, "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        access = json.loads(resp.read())["access_token"]
    rows, page, pages = [], 1, 1
    while page <= pages and page <= 50:
        q = urllib.parse.urlencode({"mid": retailer["rakuten_mid"], "keyword": retailer.get("rakuten_keyword", "watch"),
                                    "max": 100, "pagenumber": page, "sort": "retailprice", "sorttype": "dsc"})
        req = urllib.request.Request(f"{RAKUTEN_API}/productsearch/1.0?{q}", headers={"Authorization": "Bearer " + access})
        with urllib.request.urlopen(req, timeout=120) as resp:
            got, pages = rakuten_items_to_rows(resp.read().decode("utf-8", "replace"), brands)
        rows += got
        page += 1
    return rows


def awin_feed_for(retailer, template_url):
    """Build an Awin feed URL for another joined advertiser from an existing feed URL (same API key
    and columns), using Awin's feed list to find that advertiser's feed id. Never prints the key."""
    m = re.search(r"/apikey/([^/]+)/", template_url)
    if not (m and re.search(r"/fid/[\d,]+/", template_url)):
        print(f"skip {retailer['name']}: template feed URL has no apikey/fid segments")
        return ""
    try:
        with urllib.request.urlopen(f"https://productdata.awin.com/datafeed/list/apikey/{m.group(1)}", timeout=60) as r:
            rows = list(csv.DictReader(io.StringIO(r.read().decode("utf-8-sig", "replace"))))
    except Exception as exc:
        print(f"skip {retailer['name']}: Awin feed list unavailable ({type(exc).__name__})")
        return ""
    adv = str(retailer["awin_advertiser_id"])
    mine = [x for x in rows if str(x.get("Advertiser ID", "")).strip() == adv
            and str(x.get("Membership Status", "active")).strip().lower() in ("active", "joined")]
    if not mine:
        print(f"skip {retailer['name']}: no active Awin feed listed for advertiser {adv} ({len(rows)} feeds listed)")
        return ""
    best = max(mine, key=lambda x: int(re.sub(r"\D", "", str(x.get("No of products", "0"))) or 0))
    print(f"{retailer['name']}: using Awin feed {best.get('Feed ID')} ({best.get('Feed Name', '')}, {best.get('No of products', '?')} products)")
    return re.sub(r"/fid/[\d,]+/", f"/fid/{str(best.get('Feed ID')).strip()}/", template_url)


def known_brands(cfg):
    """{lower-case name or alias: display name} for brand matching in Rakuten product names."""
    names = {n.lower(): n for n in cfg.get("extra_brand_names", [])}
    try:
        for b in json.loads((ROOT / "content" / "brands.json").read_text()):
            names[b["name"].lower()] = b["name"]
            for a in b.get("aliases", []):
                if "&amp;" not in a:
                    names[a.lower()] = b["name"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return names


def apply_history(products, previous, today):
    """Carry forward the last price we saw so genuine price changes can be shown."""
    prev = {p["id"]: p for p in previous}
    for p in products:
        old = prev.get(p["id"])
        if not old:
            p["first_seen"] = today
            p["prev_price"] = None
            p["price_changed"] = None
        elif old["price"] != p["price"]:
            p["first_seen"] = old.get("first_seen", today)
            p["prev_price"] = old["price"]
            p["price_changed"] = today
        else:
            p["first_seen"] = old.get("first_seen", today)
            p["prev_price"] = old.get("prev_price")
            p["price_changed"] = old.get("price_changed")
    return products


def validate(products, previous, feed_cfg):
    if len(products) < feed_cfg["min_products"]:
        return f"only {len(products)} products (minimum {feed_cfg['min_products']})"
    if previous and len(products) < len(previous) * (1 - feed_cfg["max_drop_ratio"]):
        return f"product count fell from {len(previous)} to {len(products)}"
    return None


def main():
    cfg = json.loads((ROOT / "config.json").read_text())
    previous = []
    if OUT.exists():
        previous = json.loads(OUT.read_text()).get("products", [])
    today = dt.date.today().isoformat()
    products, used = [], []
    for retailer in cfg["retailers"]:
        url = os.environ.get(retailer["feed_env"], "").strip()
        if not url and retailer.get("network") == "rakuten" and os.environ.get("RAKUTEN_CLIENT_ID") and os.environ.get("RAKUTEN_CLIENT_SECRET"):
            url = "rakuten-api"
        if not url and retailer.get("feed_like"):
            url = awin_feed_for(retailer, os.environ.get(retailer["feed_like"], "").strip())
        if not url:
            print(f"skip {retailer['name']}: {retailer['feed_env']} not set")
            continue
        try:
            if retailer.get("network") == "rakuten":
                rows = fetch_rakuten(retailer, known_brands(cfg))
            else:
                with urllib.request.urlopen(url, timeout=120) as resp:
                    rows = map_columns(parse_feed(resp.read(), retailer.get("delimiter", ",")), retailer.get("column_map"))
        except Exception as exc:  # one retailer failing must not take the others down
            print(f"{retailer['name']}: fetch failed ({type(exc).__name__}); its listings are left out this run", file=sys.stderr)
            continue
        kept = [p for p in (normalise_row(r, retailer, cfg) for r in rows) if p]
        print(f"{retailer['name']}: {len(rows)} rows, {len(kept)} kept")
        products += kept
        used.append(retailer["id"])
    if not used:
        print("No feed URLs configured. Existing data left unchanged.")
        return 0
    seen, unique = set(), []
    for p in products:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)
    problem = validate(unique, previous, cfg["feed"])
    if problem:
        print(f"FEED REJECTED: {problem}. Existing data left unchanged.", file=sys.stderr)
        return 1
    unique = apply_history(unique, previous, today)
    unique.sort(key=lambda p: (p["brand"].lower(), p["price"]))
    OUT.write_text(json.dumps({
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "retailers": used,
        "products": unique,
    }, indent=1, ensure_ascii=False))
    print(f"wrote {len(unique)} products")
    return 0


if __name__ == "__main__":
    sys.exit(main())
