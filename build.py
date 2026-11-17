#!/usr/bin/env python3
"""Static site generator for Hourwright. Usage: python build.py  ->  dist/"""
import datetime as dt
import html
import json
import math
import os
import re
import shutil
import urllib.parse
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent
DIST = Path(os.environ.get("HW_DIST") or ROOT / "dist")
CFG = json.loads((ROOT / "config.json").read_text())
BRANDS = json.loads((ROOT / "content" / "brands.json").read_text())
DATA = json.loads(Path(os.environ.get("HW_DATA") or ROOT / "data" / "products.json").read_text())
PRODUCTS = DATA.get("products", [])
SITE = CFG["site_name"]
DOMAIN = CFG["domain"].rstrip("/")
TODAY = dt.date.today()
PAGES = []  # (path, lastmod) for the sitemap
PRELAUNCH = bool(os.environ.get("HW_PRELAUNCH"))  # deployed for review, hidden from search engines

e = html.escape


def gbp(value):
    return "£{:,.0f}".format(value) if float(value).is_integer() else "£{:,.2f}".format(value)


def nice_date(iso):
    try:
        return dt.date.fromisoformat(iso[:10]).strftime("%-d %B %Y")
    except (TypeError, ValueError):
        return ""


FETCHED = nice_date(DATA.get("fetched_at") or "")
MAX_PRICE_AGE_DAYS = 3
try:
    _age = (TODAY - dt.date.fromisoformat((DATA.get("fetched_at") or "")[:10])).days
except ValueError:
    _age = None
# If the feed has not refreshed recently, never show a price that may be out of date.
STALE = bool(PRODUCTS) and (_age is None or _age > MAX_PRICE_AGE_DAYS)


def price_html(p, big=False):
    if STALE:
        return '<p class="meta">See the current price at the retailer</p>'
    return f'<p class="price{" big" if big else ""}"><strong>{gbp(p["price"])}</strong></p>'
RETAILERS = {r["id"]: r for r in CFG["retailers"]}


def retailer_link(r):
    """Tracked link to a retailer's home page, only once a publisher ID is set."""
    pub = CFG.get("awin_publisher_id")
    if not pub:
        return r["url"]
    return ("https://www.awin1.com/cread.php?awinmid={}&awinaffid={}&ued={}"
            .format(r["awin_advertiser_id"], pub, urllib.parse.quote(r["url"], safe="")))


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower().replace("&", " and ")).strip("-")


_GENERATED = {}


def brand_for(product):
    """Editorial brand entry if we wrote a guide, otherwise a plain entry built from the feed."""
    name = product["brand"].strip()
    low = name.lower()
    for b in BRANDS:
        if low in b["aliases"] or low == b["name"].lower():
            return b
    key = slug(name)
    if key not in _GENERATED:
        _GENERATED[key] = {"slug": key, "name": name, "generated": True}
    return _GENERATED[key]


def all_brands():
    """Every brand with listings, plus editorial brands, sorted by name."""
    seen = {}
    for p in PRODUCTS:
        b = brand_for(p)
        seen.setdefault(b["slug"], b)
    for b in BRANDS:
        seen.setdefault(b["slug"], b)
    return sorted(seen.values(), key=lambda b: b["name"].lower())


# ---------------------------------------------------------------- layout

NAV = [("watches/index.html", "Watches"), ("brands/index.html", "Brands"),
       ("compare/index.html", "Compare"), ("price-drops/index.html", "Price drops"),
       ("guides/index.html", "Guides")]

FOOT = [("about.html", "About"), ("how-we-choose.html", "How we choose"),
        ("editorial-policy.html", "Editorial policy"),
        ("affiliate-disclosure.html", "Affiliate disclosure"),
        ("privacy.html", "Privacy"), ("cookies.html", "Cookies"),
        ("terms.html", "Terms"), ("contact.html", "Contact")]


def dial_svg():
    """A plain watch dial: 60 minute ticks, 12 hour indices, hands at ten past ten."""
    ticks = []
    for i in range(60):
        a = math.radians(i * 6)
        hour = i % 5 == 0
        r1, r2 = (78, 92) if hour else (87, 92)
        ticks.append('<line x1="{:.2f}" y1="{:.2f}" x2="{:.2f}" y2="{:.2f}" class="{}"/>'.format(
            100 + r1 * math.sin(a), 100 - r1 * math.cos(a),
            100 + r2 * math.sin(a), 100 - r2 * math.cos(a), "h" if hour else "m"))

    def hand(deg, length, cls):
        a = math.radians(deg)
        return '<line x1="100" y1="100" x2="{:.2f}" y2="{:.2f}" class="{}"/>'.format(
            100 + length * math.sin(a), 100 - length * math.cos(a), cls)
    return ('<svg class="dial" viewBox="0 0 200 200" role="img" aria-label="Watch dial">'
            '<circle cx="100" cy="100" r="98" class="case"/>'
            '<circle cx="100" cy="100" r="94" class="face"/>' + "".join(ticks) +
            hand(305, 46, "hour") + hand(60, 68, "minute") + hand(210, 74, "second") +
            '<circle cx="100" cy="100" r="3.5" class="pin"/></svg>')


def page(path, title, desc, body, *, jsonld=None, noindex=False, crumbs=None, og_type="website"):
    noindex = noindex or PRELAUNCH
    depth = path.count("/")
    r = "/" if path == "404.html" else "../" * depth  # 404 is served at any depth
    canonical = f"{DOMAIN}/" if path == "index.html" else f"{DOMAIN}/{path}"
    full_title = title if SITE in title else f"{title} | {SITE}"
    nav = "".join('<a href="{}{}"{}>{}</a>'.format(
        r, href, ' aria-current="page"' if path.startswith(href.split("/")[0] + "/") else "", label)
        for href, label in NAV)
    foot = "".join(f'<a href="{r}{href}">{label}</a>' for href, label in FOOT)
    ld = list(jsonld or [])
    crumb_html = ""
    if crumbs:
        trail = [("index.html", "Home")] + crumbs
        crumb_html = '<nav class="crumbs" aria-label="Breadcrumb">' + " / ".join(
            f'<a href="{r}{h}">{e(l)}</a>' if h else f"<span>{e(l)}</span>" for h, l in trail) + "</nav>"
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList",
                   "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": l,
                                        "item": f"{DOMAIN}/{h}" if h else canonical}
                                       for i, (h, l) in enumerate(trail)]})
    ld_html = "".join('<script type="application/ld+json">{}</script>'.format(
        json.dumps(x, ensure_ascii=False).replace("</", "<\\/")) for x in ld)
    verify = ""
    if CFG.get("google_site_verification"):
        verify += f'<meta name="google-site-verification" content="{e(CFG["google_site_verification"])}">'
    if CFG.get("bing_site_verification"):
        verify += f'<meta name="msvalidate.01" content="{e(CFG["bing_site_verification"])}">'
    signup = ""
    if CFG.get("email_form_action"):
        signup = f"""<section class="signup"><div class="wrap">
<h2>Price drops, by email</h2>
<p>One email when retailer prices fall on watches in our range. Unsubscribe in one click.</p>
<form action="{e(CFG['email_form_action'])}" method="post" target="_blank" rel="noopener">
<label for="signup-email">Email address</label>
<div class="row"><input id="signup-email" type="email" name="{e(CFG['email_form_field'])}" required autocomplete="email" placeholder="you@example.co.uk">
<button class="btn" type="submit">Send me price drops</button></div>
<p class="fine">We use your address only for this email. See our <a href="{r}privacy.html">privacy notice</a>.</p>
</form></div></section>"""
    operator = e(CFG.get("operator_legal_name") or "")
    out = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
{'<meta name="robots" content="noindex">' if noindex else f'<link rel="canonical" href="{canonical}">'}
<meta property="og:site_name" content="{e(SITE)}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="en_GB">
<meta name="twitter:card" content="summary">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' https: data:; script-src 'self' https://www.googletagmanager.com; style-src 'self'; font-src 'self'; connect-src 'self' https://*.google-analytics.com https://www.googletagmanager.com; form-action 'self' https:; base-uri 'self'; object-src 'none'">
{verify}
<link rel="preload" href="{r}fonts/hanken-grotesk-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{r}css/site.css">
<link rel="icon" href="{r}favicon.svg" type="image/svg+xml">
{ld_html}
</head>
<body data-root="{r}" data-ga="{e(CFG.get('ga4_measurement_id') or '')}">
<a class="skip" href="#main">Skip to content</a>
<p class="disclosure"><span class="wrap">We may earn a commission when you buy from a retailer through our links. It never changes the price you pay. <a href="{r}affiliate-disclosure.html">How we are funded</a></span></p>
<header class="site-head"><div class="wrap">
<a class="brand" href="{r}index.html">{e(SITE)}</a>
<button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button>
<nav id="site-nav" aria-label="Main">{nav}</nav>
</div></header>
<main id="main">
{crumb_html}
{body}
</main>
{signup}
<footer class="site-foot"><div class="wrap">
<p class="brand">{e(SITE)}</p>
<p>{e(CFG['tagline'])} {e(SITE)} is not a retailer. Prices, stock and specifications are supplied by the retailers we link to and can change; always confirm on the retailer's site before buying.</p>
<nav aria-label="Site information">{foot}</nav>
<p class="fine">&copy; {TODAY.year} {operator or e(SITE)}. Brand and model names are trademarks of their owners and are used to identify products only. {e(SITE)} is independent and is not affiliated with or endorsed by any watch brand.</p>
</div></footer>
<div id="consent" class="consent" hidden role="dialog" aria-label="Analytics cookies">
<p>We would like to use analytics cookies to see which pages are useful. They are off unless you accept. <a href="{r}cookies.html">Cookie details</a></p>
<div class="row"><button class="btn" type="button" id="consent-yes">Accept analytics</button><button class="btn ghost" type="button" id="consent-no">Reject</button></div>
</div>
<script src="{r}js/site.js" defer></script>
</body>
</html>
"""
    target = DIST / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(out, encoding="utf-8")
    if not noindex:
        PAGES.append(path)


# ---------------------------------------------------------------- components

def card(p, r):
    b = brand_for(p)
    stock = {True: "In stock", False: "Out of stock"}.get(p.get("in_stock"), "")
    img = (f'<img src="{e(p["image"])}" alt="{e(p["brand"] + " " + p["name"])}" loading="lazy" '
           f'width="320" height="320" referrerpolicy="no-referrer">') if p.get("image") else '<span class="noimg">No image supplied</span>'
    return f"""<article class="card" data-id="{e(p['id'])}" data-brand="{e(b['slug'])}" data-retailer="{e(p['retailer'])}" data-price="{p['price']}" data-text="{e((p['brand'] + ' ' + p['name'] + ' ' + (p.get('reference') or '')).lower())}">
<a class="thumb" href="{r}watches/{e(p['slug'])}.html">{img}</a>
<p class="eyebrow">{e(p['brand'])}</p>
<h3><a href="{r}watches/{e(p['slug'])}.html">{e(p['name'])}</a></h3>
{price_html(p)}
<p class="meta">{e(p['retailer_name'])}{' · ' + stock if stock else ''} · <a href="{r}affiliate-disclosure.html">Affiliate link</a></p>
<div class="row"><a class="btn" href="{e(p['link'])}" rel="sponsored nofollow noopener" target="_blank" data-aff="{e(p['retailer'])}" data-pid="{e(p['id'])}">View at {e(p['retailer_name'])}</a>
<label class="pick"><input type="checkbox" class="compare-pick" value="{e(p['id'])}"> Compare</label></div>
</article>"""


def grid(products, r):
    return '<div class="grid">' + "".join(card(p, r) for p in products) + "</div>"


def checked_note():
    if STALE:
        return '<p class="checked">Retailer prices are being refreshed, so we are not showing them at the moment. Follow a link to see the current price.</p>'
    if not FETCHED:
        return ""
    return f'<p class="checked">Retailer prices last checked {FETCHED}. Confirm the current price on the retailer\'s site.</p>'


EMPTY = ('<div class="empty"><h2>Listings are being connected</h2>'
         "<p>We only publish prices, stock and specifications supplied directly by authorised retailers "
         "through their official product feeds. Listings appear here as soon as those feeds are live.</p></div>")


def retailer_strip(r):
    items = "".join(
        f'<li><a href="{e(retailer_link(x))}" rel="sponsored nofollow noopener" target="_blank" data-aff="{e(x["id"])}">{e(x["name"])}</a></li>'
        for x in CFG["retailers"] if x.get("status") == "live")
    return f'<ul class="retailers">{items}</ul>' if items else ""


# ---------------------------------------------------------------- pages

def build_home():
    brand_links = "".join(
        f'<li><a href="brands/{b["slug"]}.html"><strong>{e(b["name"])}</strong><span>{e(b["summary"])}</span></a></li>'
        for b in BRANDS[:8])
    guides = load_guides()
    guide_links = "".join(
        f'<li><a href="guides/{g["slug"]}.html"><strong>{e(g["title"])}</strong><span>{e(g["description"])}</span></a></li>'
        for g in guides[:4])
    latest = sorted(PRODUCTS, key=lambda p: p.get("first_seen") or "", reverse=True)[:8]
    count = (f"{len(PRODUCTS):,} watches from {len({p['brand'] for p in PRODUCTS})} brands, "
             f"priced by {len({p['retailer'] for p in PRODUCTS})} UK retailers.") if PRODUCTS else ""
    floor = gbp(CFG["price_floor_gbp"])
    body = f"""<section class="hero"><div class="wrap">
<div>
<p class="eyebrow">UK authorised retailers only</p>
<h1>Find the right watch. Then find the right price for it.</h1>
<p class="lede">{e(SITE)} compares luxury watches from {floor} across UK authorised retailers, with the retailer's own price beside each one and guides written in plain English.</p>
<p class="row"><a class="btn" href="watches/index.html">Browse watches</a><a class="btn ghost" href="compare/index.html">Compare side by side</a></p>
<p class="fine">{count}</p>
</div>
{dial_svg()}
</div></section>
<section class="band"><div class="wrap three">
<div><h2>Authorised stock</h2><p>Every watch we list is sold new by a retailer that states it is authorised by the brand, so the manufacturer's warranty applies.</p></div>
<div><h2>The retailer's price</h2><p>Prices come straight from retailer product feeds and carry the date we last checked them. We never estimate a price.</p></div>
<div><h2>Independent guidance</h2><p>Retailers cannot pay to change what we write or how watches are ordered. <a href="how-we-choose.html">How we choose</a></p></div>
</div></section>
{'<section><div class="wrap"><h2>Newly listed</h2>' + grid(latest, "") + checked_note() + '</div></section>' if latest else ''}
<section><div class="wrap"><h2>Brands</h2><ul class="links">{brand_links}</ul>
<p><a class="more" href="brands/index.html">All brands</a></p></div></section>
<section><div class="wrap"><h2>Buying guides</h2><ul class="links">{guide_links}</ul>
<p><a class="more" href="guides/index.html">All guides</a></p></div></section>"""
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": SITE, "url": DOMAIN + "/"},
          {"@context": "https://schema.org", "@type": "Organization", "name": SITE, "url": DOMAIN + "/"}]
    page("index.html", f"{SITE}: luxury watches from UK authorised retailers, compared", CFG["description"], body, jsonld=ld)


def filters():
    counts = {}
    for p in PRODUCTS:
        k = brand_for(p)["slug"]
        counts[k] = counts.get(k, 0) + 1
    brand_opts = "".join(f'<option value="{b["slug"]}">{e(b["name"])} ({counts[b["slug"]]})</option>'
                         for b in all_brands() if b["slug"] in counts)
    ret_opts = "".join(f'<option value="{rid}">{e(RETAILERS[rid]["name"])}</option>'
                       for rid in sorted({p["retailer"] for p in PRODUCTS}) if rid in RETAILERS)
    return f"""<form class="filters" id="filters" aria-label="Filter watches">
<div><label for="f-q">Search</label><input id="f-q" type="search" placeholder="Model or reference" autocomplete="off"></div>
<div><label for="f-brand">Brand</label><select id="f-brand"><option value="">All brands</option>{brand_opts}</select></div>
<div><label for="f-retailer">Retailer</label><select id="f-retailer"><option value="">All retailers</option>{ret_opts}</select></div>
<div><label for="f-price">Price</label><select id="f-price"><option value="">Any price</option>
<option value="0-3000">Under £3,000</option><option value="3000-5000">£3,000 to £5,000</option>
<option value="5000-10000">£5,000 to £10,000</option><option value="10000-15000">£10,000 to £15,000</option>
<option value="15000-">£15,000 and over</option></select></div>
<div><label for="f-sort">Sort</label><select id="f-sort"><option value="">Brand A to Z</option>
<option value="asc">Price, low to high</option><option value="desc">Price, high to low</option></select></div>
<p class="count" id="f-count" aria-live="polite"></p>
</form>"""


def build_watches():
    floor = gbp(CFG["price_floor_gbp"])
    body = f"""<section><div class="wrap"><h1>Luxury watches</h1>
<p class="lede">New watches from {floor}, sold by UK authorised retailers. Tick Compare on up to three to see them side by side.</p>
{(filters() + '<h2 class="sr">Results</h2>' + grid(PRODUCTS, "../") + checked_note()) if PRODUCTS else EMPTY}
</div></section>"""
    page("watches/index.html", "Luxury watches from UK authorised retailers",
         f"Browse new luxury watches from {floor} at UK authorised retailers, with each retailer's current price.",
         body, crumbs=[("", "Watches")])
    for p in PRODUCTS:
        build_product(p)


def build_product(p):
    b = brand_for(p)
    same = [x for x in PRODUCTS if p.get("group") and x.get("group") == p["group"] and x["id"] != p["id"]]
    rows = [("Brand", p["brand"]), ("Reference", p.get("reference")), ("Colour", p.get("colour")),
            ("Retailer", p["retailer_name"]),
            ("Availability", {True: "In stock", False: "Out of stock"}.get(p.get("in_stock")))]
    spec = "".join(f"<tr><th scope=\"row\">{e(k)}</th><td>{e(v)}</td></tr>" for k, v in rows if v)
    img = (f'<img src="{e(p["image"])}" alt="{e(p["brand"] + " " + p["name"])}" width="560" height="560" '
           f'referrerpolicy="no-referrer">') if p.get("image") else ""
    others = ""
    if same and not STALE:
        offers = sorted(same + [p], key=lambda x: x["price"])
        others = "<h2>This model at other retailers</h2><table class=\"offers\"><tbody>" + "".join(
            f'<tr><th scope="row">{e(x["retailer_name"])}</th><td class="num">{gbp(x["price"])}</td>'
            f'<td><a href="{e(x["link"])}" rel="sponsored nofollow noopener" target="_blank" data-aff="{e(x["retailer"])}" data-pid="{e(x["id"])}">View</a></td></tr>'
            for x in offers) + "</tbody></table>"
    body = f"""<article class="product"><div class="wrap">
<div class="shot">{img}</div>
<div>
<p class="eyebrow">{f'<a href="../brands/{b["slug"]}.html">{e(p["brand"])}</a>' if b else e(p['brand'])}</p>
<h1>{e(p['name'])}</h1>
{price_html(p, big=True)}
{'' if STALE else '<p class="meta">Price supplied by ' + e(p['retailer_name']) + (', checked ' + FETCHED if FETCHED else '') + '.</p>'}
<p class="row"><a class="btn" href="{e(p['link'])}" rel="sponsored nofollow noopener" target="_blank" data-aff="{e(p['retailer'])}" data-pid="{e(p['id'])}">View at {e(p['retailer_name'])}</a>
<label class="pick"><input type="checkbox" class="compare-pick" value="{e(p['id'])}"> Compare</label></p>
<p class="fine">This is an affiliate link. We may earn a commission if you buy.</p>
<table class="spec"><tbody>{spec}</tbody></table>
{'<h2>Retailer description</h2><p>' + e(p['description']) + '</p>' if p.get('description') else ''}
{'<h2>Specifications</h2><p>' + e(p['specifications']) + '</p>' if p.get('specifications') else ''}
{others}
</div></div></article>"""
    offer = {"@type": "Offer", "price": p["price"], "priceCurrency": "GBP", "url": f"{DOMAIN}/watches/{p['slug']}.html",
             "seller": {"@type": "Organization", "name": p["retailer_name"]}}
    if p.get("in_stock") is not None:
        offer["availability"] = "https://schema.org/" + ("InStock" if p["in_stock"] else "OutOfStock")
    ld = {"@context": "https://schema.org", "@type": "Product", "name": p["name"],
          "brand": {"@type": "Brand", "name": p["brand"]}}
    if not STALE:
        ld["offers"] = offer
    if p.get("image"):
        ld["image"] = p["image"]
    if p.get("reference"):
        ld["mpn"] = p["reference"]
    crumbs = [("watches/index.html", "Watches")] + ([(f"brands/{b['slug']}.html", b["name"])] if b else []) + [("", p["name"])]
    page(f"watches/{p['slug']}.html", f"{p['brand']} {p['name']}",
         f"{p['brand']} {p['name']} at {p['retailer_name']}. Compare this watch across UK authorised retailers.",
         body, jsonld=[ld], crumbs=crumbs, og_type="product")


def build_brands():
    counts, lows = {}, {}
    for p in PRODUCTS:
        k = brand_for(p)["slug"]
        counts[k] = counts.get(k, 0) + 1
        lows[k] = min(lows.get(k, p["price"]), p["price"])
    def blurb(b):
        n = counts.get(b["slug"], 0)
        listed = f"{n} {'watch' if n == 1 else 'watches'} from {gbp(lows[b['slug']])}" if n else "No current listings"
        return f"{b['summary']} {listed}." if not b.get("generated") else f"{listed}."
    items = "".join(
        f'<li><a href="{b["slug"]}.html"><strong>{e(b["name"])}</strong><span>{e(blurb(b))}</span></a></li>'
        for b in all_brands())
    page("brands/index.html", "Luxury watch brands",
         "Every luxury watch brand we list from UK authorised retailers, with current listings and brand guides.",
         f'<section><div class="wrap"><h1>Brands</h1><p class="lede">Every brand with new watches from {gbp(CFG["price_floor_gbp"])} at our retailers, plus guides to the major makers.</p><ul class="links">{items}</ul></div></section>',
         crumbs=[("", "Brands")])
    for b in all_brands():
        mine = [p for p in PRODUCTS if brand_for(p) is b]
        none_now = (f'<div class="empty"><h2>No current listings</h2><p>Our retailers do not list new {e(b["name"])} watches '
                    f'from {gbp(CFG["price_floor_gbp"])} at the moment. Listings are checked daily.</p></div>') if PRODUCTS else EMPTY
        listing = f'<h2>{e(b["name"])} watches at UK retailers</h2>' + ((grid(mine, "../") + checked_note()) if mine else none_now)
        if b.get("generated"):
            n = len(mine)
            body = f"""<section><div class="wrap">
<p class="eyebrow">Brand</p><h1>{e(b['name'])}</h1>
<p class="lede">{n} new {e(b['name'])} {'watch' if n == 1 else 'watches'} from {gbp(lows[b['slug']])} at UK authorised retailers, with each retailer's own price.</p>
{listing}
</div></section>"""
            page(f"brands/{b['slug']}.html", f"{b['name']} watches: UK prices",
                 f"New {b['name']} watches from UK authorised retailers, with current retailer prices.",
                 body, crumbs=[("brands/index.html", "Brands"), ("", b["name"])])
            continue
        paras = "".join(f"<p>{e(x)}</p>" for x in b["body"])
        lines = "".join(f"<li>{e(x)}</li>" for x in b["lines"])
        body = f"""<section><div class="wrap">
<p class="eyebrow">Brand guide</p><h1>{e(b['name'])}</h1>
<p class="lede">{e(b['summary'])}</p>
<div class="two"><div class="prose">{paras}</div>
<aside class="facts"><dl><dt>Founded</dt><dd>{e(b['founded'])}</dd><dt>Based</dt><dd>{e(b['home'])}</dd></dl>
<h2>Key collections</h2><ul>{lines}</ul></aside></div>
{listing}
</div></section>"""
        page(f"brands/{b['slug']}.html", f"{b['name']} watches: brand guide and UK prices",
             f"{b['name']} watches from UK authorised retailers. {b['summary']}",
             body, crumbs=[("brands/index.html", "Brands"), ("", b["name"])])


def load_guides():
    guides = []
    for f in sorted((ROOT / "content" / "guides").glob("*.md")):
        head, text = f.read_text(encoding="utf-8").split("\n---\n", 1)
        meta = dict(line.split(": ", 1) for line in head.strip().splitlines())
        meta.update(slug=f.stem, html=markdown.markdown(text), mtime=dt.date.fromtimestamp(f.stat().st_mtime))
        guides.append(meta)
    return sorted(guides, key=lambda g: int(g.get("order", 99)))


def build_guides():
    guides = load_guides()
    items = "".join(
        f'<li><a href="{g["slug"]}.html"><strong>{e(g["title"])}</strong><span>{e(g["description"])}</span></a></li>'
        for g in guides)
    page("guides/index.html", "Luxury watch buying guides",
         "Plain-English guides to buying a luxury watch in the UK: movements, sizing, water resistance, certification and running costs.",
         f'<section><div class="wrap"><h1>Buying guides</h1><p class="lede">Written to help you compare, not to sell you a particular watch.</p><ul class="links">{items}</ul></div></section>',
         crumbs=[("", "Guides")])
    for g in guides:
        related = "".join(f'<li><a href="{x["slug"]}.html">{e(x["title"])}</a></li>' for x in guides if x is not g)
        body = f"""<article><div class="wrap narrow">
<p class="eyebrow">Buying guide</p><h1>{e(g['title'])}</h1>
<p class="lede">{e(g['description'])}</p>
<p class="meta">Reviewed {g['mtime'].strftime('%-d %B %Y')} · <a href="../editorial-policy.html">Editorial policy</a></p>
<div class="prose">{g['html']}</div>
<p class="row"><a class="btn" href="../watches/index.html">Browse watches</a><a class="btn ghost" href="../compare/index.html">Compare side by side</a></p>
<h2>More guides</h2><ul class="plain">{related}</ul>
</div></article>"""
        ld = {"@context": "https://schema.org", "@type": "Article", "headline": g["title"],
              "description": g["description"], "dateModified": g["mtime"].isoformat(),
              "author": {"@type": "Organization", "name": SITE},
              "publisher": {"@type": "Organization", "name": SITE},
              "mainEntityOfPage": f"{DOMAIN}/guides/{g['slug']}.html"}
        page(f"guides/{g['slug']}.html", g["title"], g["description"], body, jsonld=[ld],
             crumbs=[("guides/index.html", "Guides"), ("", g["title"])], og_type="article")


def build_compare():
    body = f"""<section><div class="wrap"><h1>Compare watches</h1>
<p class="lede">Up to three watches side by side, using the details each retailer supplies.</p>
<div id="compare" data-empty="{'feed' if not PRODUCTS else 'pick'}">
{EMPTY if not PRODUCTS else '<div class="empty"><h2>Nothing to compare yet</h2><p>Tick Compare on any watch in the <a href="../watches/index.html">listings</a> and it will appear here.</p></div>'}
</div>
{checked_note()}
<noscript><p>The comparison table needs JavaScript. Every watch also has its own page with full details.</p></noscript>
</div></section>"""
    page("compare/index.html", "Compare luxury watches side by side",
         "Compare up to three luxury watches side by side: price, retailer, reference and availability from UK authorised retailers.",
         body, crumbs=[("", "Compare")])


def build_drops():
    cutoff = (TODAY - dt.timedelta(days=14)).isoformat()
    drops = [] if STALE else [p for p in PRODUCTS if p.get("prev_price") and p.get("price_changed")
             and p["price_changed"] >= cutoff and p["price"] < p["prev_price"]]
    drops.sort(key=lambda p: p["prev_price"] - p["price"], reverse=True)
    if drops:
        rows = "".join(
            f'<tr><th scope="row"><a href="../watches/{e(p["slug"])}.html">{e(p["brand"])} {e(p["name"])}</a></th>'
            f'<td>{e(p["retailer_name"])}</td><td class="num"><s>{gbp(p["prev_price"])}</s></td>'
            f'<td class="num"><strong>{gbp(p["price"])}</strong></td><td>{nice_date(p["price_changed"])}</td></tr>'
            for p in drops)
        inner = ('<div class="scroll"><table class="offers"><thead><tr><th>Watch</th><th>Retailer</th>'
                 '<th class="num">Was</th><th class="num">Now</th><th>Changed</th></tr></thead>'
                 f"<tbody>{rows}</tbody></table></div>" + checked_note())
    elif PRODUCTS:
        inner = '<div class="empty"><h2>No price drops in the last 14 days</h2><p>We check retailer prices daily and list every fall here.</p></div>'
    else:
        inner = EMPTY
    body = f"""<section><div class="wrap"><h1>Price drops</h1>
<p class="lede">Watches whose retailer price has fallen in the last 14 days. "Was" is the price the same retailer listed on our previous check.</p>
{inner}</div></section>"""
    page("price-drops/index.html", "Luxury watch price drops",
         "Luxury watches whose price has fallen at UK authorised retailers in the last 14 days, checked daily.",
         body, crumbs=[("", "Price drops")])


def build_static():
    op = e(CFG.get("operator_legal_name") or "[operator name to be added before launch]")
    addr = e(CFG.get("operator_address") or "[postal address to be added before launch]")
    mail = e(CFG.get("contact_email") or "[contact email to be added before launch]")
    names = ", ".join(r["name"] for r in CFG["retailers"] if r.get("status") == "live") or "the retailers named on each listing"
    floor = gbp(CFG["price_floor_gbp"])
    docs = {
        "about.html": ("About " + SITE, f"What {SITE} is, who it is for and how it works.", f"""
<p>{e(SITE)} is a comparison and buying-guide site for new luxury watches sold in the UK. We are not a retailer and we do not hold stock. We show you what authorised retailers are selling and at what price, and we explain the differences that matter.</p>
<h2>How it works</h2>
<ol><li>Browse by brand or price, or read a guide.</li><li>Compare up to three watches side by side.</li><li>Follow the link to the retailer to check the current price and buy from them directly.</li></ol>
<h2>What we list</h2>
<p>New watches from {floor}, sold by retailers that state they are authorised by the brand. We do not list grey-market or pre-owned sellers.</p>
<h2>Who runs it</h2>
<p>{e(SITE)} is operated by {op}, {addr}. You can reach us at {mail}.</p>"""),
        "how-we-choose.html": ("How we choose", "How watches and retailers are selected and ordered on " + SITE + ".", f"""
<h2>Which retailers</h2>
<p>We list retailers that state they are authorised stockists of the brands they sell and that publish an official product feed. That feed is the only source of the prices, stock status and specifications we show.</p>
<p>We do not cover every UK retailer or every watch on sale. We only list retailers we have an affiliate relationship with, so a lower price may be available elsewhere.</p>
<h2>Which watches</h2>
<p>Any new watch priced from {floor} in a listed retailer's feed. We do not hand-pick products for commercial reasons.</p>
<h2>How listings are ordered</h2>
<p>By brand name, then price, unless you choose a different sort. Commission rates play no part in the order and retailers cannot pay for position.</p>
<h2>Prices</h2>
<p>Each price is the retailer's own, with the date we last checked it. Retailers change prices without notice, so confirm on their site. We do not show retailers' "was" or recommended prices on listings. If our price data is more than three days old we hide prices until it is refreshed. On the price drops page, "was" is the price the same retailer listed at our previous check.</p>
<h2>What we do not do</h2>
<p>We do not invent or estimate prices, specifications or availability, and we do not publish reviews of watches we have not handled.</p>"""),
        "editorial-policy.html": ("Editorial policy", "How " + SITE + " guides are written, checked and corrected.", f"""
<h2>Independence</h2>
<p>Our guides are written to help you compare. Retailers and brands do not see them before publication and cannot pay to change them.</p>
<h2>Sources</h2>
<p>Brand histories and technical explanations are drawn from manufacturers' published material and recognised standards bodies. Product details on listings come from retailer feeds and are shown as supplied.</p>
<h2>Use of AI</h2>
<p>We use AI tools to help draft and maintain content. Every guide is checked against its sources before publication, and we take responsibility for what we publish.</p>
<h2>Corrections</h2>
<p>If you find an error, email {mail}. We correct confirmed mistakes promptly and update the review date on the page.</p>"""),
        "affiliate-disclosure.html": ("Affiliate disclosure", "How " + SITE + " is funded and what that means for you.", f"""
<p>{e(SITE)} is funded by affiliate commission. When you follow a link from this site to a retailer and buy something, the retailer may pay us a commission through the Awin affiliate network. This applies to links to {e(names)}.</p>
<h2>What this means for you</h2>
<ul><li>You pay the same price as you would by going to the retailer directly.</li><li>Your contract of sale is with the retailer, who is responsible for delivery, returns and warranty.</li><li>Links that can earn commission are marked and carry a notice nearby. A notice also appears at the top of every page.</li></ul>
<h2>What it does not change</h2>
<p>Commission does not affect which watches we list, the order they appear in or what our guides say. See <a href="how-we-choose.html">how we choose</a>.</p>
<h2>Tracking</h2>
<p>When you follow a retailer link, Awin and the retailer may set cookies on their own sites to attribute the sale. See our <a href="cookies.html">cookie notice</a>.</p>"""),
        "privacy.html": ("Privacy notice", "What personal data " + SITE + " collects and how it is used.", f"""
<p>This notice explains how {op} ("we") handles personal data on {e(SITE)}. We are the data controller. Contact: {mail}, {addr}.</p>
<h2>What we collect</h2>
<ul><li><strong>Email address</strong>, if you sign up for price-drop emails. Lawful basis: your consent. You can unsubscribe at any time using the link in every email.</li>
<li><strong>Analytics data</strong>, only if you accept analytics cookies: pages viewed, approximate location, device type and which retailer links are followed. Lawful basis: your consent.</li>
<li><strong>Server logs</strong> kept by our hosting provider, including IP address, for security and reliability. Lawful basis: legitimate interests.</li></ul>
<h2>What we do not collect</h2>
<p>We do not take payments, and we do not receive your name, address or payment details from retailers. Purchases happen on the retailer's site under its own privacy notice.</p>
<h2>Who we share data with</h2>
<p>Service providers who process data on our behalf: our hosting provider, our email service and, if you consent, our analytics provider. Some may process data outside the UK under appropriate safeguards.</p>
<h2>How long we keep it</h2>
<p>Email addresses until you unsubscribe. Analytics data for up to 14 months.</p>
<h2>Your rights</h2>
<p>Under UK data protection law you can ask for access to your data, correction, erasure, restriction or a copy, and you can object to processing or withdraw consent. Email {mail}. You can also complain to the Information Commissioner's Office at ico.org.uk.</p>
<p class="meta">Last updated {TODAY.strftime('%-d %B %Y')}.</p>"""),
        "cookies.html": ("Cookie notice", "The cookies and similar storage " + SITE + " uses, and how to change your choice.", """
<h2>Strictly necessary</h2>
<p>We store your cookie choice and your comparison list in your browser's local storage. These stay on your device and are needed for the site to work as you expect.</p>
<h2>Analytics (optional)</h2>
<p>If you accept, Google Analytics sets cookies to measure which pages are used and which retailer links are followed. They are not set unless you accept.</p>
<p><button class="btn ghost" type="button" id="consent-reset">Change my cookie choice</button></p>
<h2>Retailer and affiliate cookies</h2>
<p>When you follow a link to a retailer, the Awin affiliate network and the retailer may set cookies on their own sites so the retailer can attribute a sale to us. We do not control those cookies. See each retailer's cookie notice.</p>"""),
        "terms.html": ("Terms of use", "The terms on which " + SITE + " is provided.", f"""
<p>{e(SITE)} is operated by {op}. By using the site you accept these terms.</p>
<h2>Information only</h2>
<p>We provide information to help you compare watches. We are not a retailer and are not a party to any purchase you make. Nothing on this site is financial advice.</p>
<h2>Prices and details</h2>
<p>Prices, availability and specifications are supplied by retailers and can change or contain errors. The retailer's own site is the authority. Check it before you buy.</p>
<h2>Links</h2>
<p>We link to retailer sites we do not control and are not responsible for their content or service.</p>
<h2>Intellectual property</h2>
<p>Our text and design are ours. Brand names, model names and product images belong to their owners and are used to identify products.</p>
<h2>Liability</h2>
<p>We take care to be accurate but provide the site as is. Nothing in these terms limits liability that cannot be limited under UK law.</p>
<h2>Law</h2>
<p>These terms are governed by the law of England and Wales.</p>"""),
        "contact.html": ("Contact", "How to contact " + SITE + ".", f"""
<p>Email: {mail}</p><p>Post: {op}, {addr}</p>
<p>For questions about an order, delivery, return or warranty, contact the retailer you bought from. We do not sell watches and cannot see your order.</p>"""),
    }
    for path, (title, desc, inner) in docs.items():
        page(path, title, desc,
             f'<article><div class="wrap narrow"><h1>{e(title)}</h1><div class="prose">{inner}</div></div></article>',
             crumbs=[("", title)])
    page("404.html", "Page not found", "This page could not be found.",
         '<section><div class="wrap narrow"><h1>Page not found</h1><p class="lede">That page has moved or no longer exists.</p>'
         '<p class="row"><a class="btn" href="/index.html">Go to the home page</a></p></div></section>', noindex=True)


def build_meta():
    urls = "".join(f"<url><loc>{DOMAIN}/{'' if p == 'index.html' else p}</loc><lastmod>{TODAY.isoformat()}</lastmod></url>" for p in PAGES)
    (DIST / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n" + ("" if PRELAUNCH else f"\nSitemap: {DOMAIN}/sitemap.xml\n"))
    (DIST / "CNAME").write_text(urllib.parse.urlparse(DOMAIN).netloc + "\n")
    (DIST / ".nojekyll").write_text("")
    (DIST / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><circle cx="16" cy="16" r="15" fill="#0e3b30"/>'
        '<circle cx="16" cy="16" r="11.5" fill="none" stroke="#d8b25a" stroke-width="1.5"/>'
        '<path d="M16 16 10.5 11M16 16l6.5-3.5" stroke="#f1f4f2" stroke-width="2" stroke-linecap="round"/></svg>')
    slim = [{k: p.get(k) for k in ("id", "slug", "brand", "name", "price", "retailer_name",
                                   "retailer", "in_stock", "link", "image", "reference", "colour")} for p in PRODUCTS]
    if STALE:
        for item in slim:
            item["price"] = None
            item["in_stock"] = None
    (DIST / "data").mkdir(exist_ok=True)
    (DIST / "data" / "products.json").write_text(json.dumps(slim, ensure_ascii=False))


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for sub in ("css", "js", "fonts"):
        shutil.copytree(ROOT / "static" / sub, DIST / sub)
    build_home()
    build_watches()
    build_brands()
    build_guides()
    build_compare()
    build_drops()
    build_static()
    build_meta()
    print(f"built {len(PAGES)} indexable pages, {len(PRODUCTS)} products -> {DIST}")


if __name__ == "__main__":
    main()
