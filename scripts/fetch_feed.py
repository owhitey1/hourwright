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
    if not link.startswith("https://www.awin1.com/"):
        return None  # only genuine Awin tracking links are ever published
    if currency != "GBP":
        return None
    if price < cfg["price_floor_gbp"]:
        return None
    if cfg.get("price_ceiling_gbp") and price > cfg["price_ceiling_gbp"]:
        return None
    if not is_watch(row, feed_cfg):
        return None
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


def parse_feed(raw_bytes):
    if raw_bytes[:2] == b"\x1f\x8b":
        raw_bytes = gzip.decompress(raw_bytes)
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


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
        if not url:
            print(f"skip {retailer['name']}: {retailer['feed_env']} not set")
            continue
        with urllib.request.urlopen(url, timeout=120) as resp:
            rows = parse_feed(resp.read())
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
