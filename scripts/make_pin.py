#!/usr/bin/env python3
"""Make an original typographic Hourwright Pinterest pin (1000 x 1500 PNG) in the site's
colours and fonts. No retailer or brand photography is used.

Usage: python3 scripts/make_pin.py --eyebrow "BUYING GUIDE" --title "..." --subtitle "..." --out ops/pinterest/x.png
Requires: pillow, fonttools, brotli (to read the site's woff2 fonts).
"""
import argparse
import pathlib
import tempfile

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
BG, BRASS, WHITE, GREY = "#0e3b30", "#d8b25a", "#f4f5f3", "#d4dbd7"
W, H, M = 1000, 1500, 92


def ttf(name):
    out = pathlib.Path(tempfile.gettempdir()) / f"hw-{name}.ttf"
    if not out.exists():
        f = TTFont(ROOT / "static" / "fonts" / f"{name}-latin-wght-normal.woff2")
        f.flavor = None
        f.save(out)
    return str(out)


def font(name, size, weight):
    f = ImageFont.truetype(ttf(name), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def wrap(draw, text, f, width):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=f) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def make(eyebrow, title, subtitle, out):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    eb = font("hanken-grotesk", 34, 500)
    x = M
    for ch in eyebrow.upper():
        d.text((x, 116), ch, font=eb, fill=BRASS)
        x += d.textlength(ch, font=eb) + 5
    size = 112
    while True:
        tf = font("fraunces", size, 620)
        lines = wrap(d, title, tf, W - 2 * M)
        if len(lines) <= 4 or size <= 72:
            break
        size -= 8
    y = 200
    for ln in lines:
        d.text((M, y), ln, font=tf, fill=WHITE)
        y += int(size * 1.03)
    sf = font("hanken-grotesk", 40, 400)
    y += 40
    for ln in wrap(d, subtitle, sf, W - 2 * M - 40):
        d.text((M, y), ln, font=sf, fill=GREY)
        y += 62
    d.text((M, 1272), "Hourwright", font=font("fraunces", 60, 500), fill=WHITE)
    d.text((M, 1346), "hourwright.co.uk", font=font("hanken-grotesk", 36, 400), fill=BRASS)
    cx, cy, r = 774, 1254, 133
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=BRASS, width=6)
    d.line([(cx, cy), (cx - 68, cy - 56)], fill=WHITE, width=6)
    d.line([(cx, cy), (cx + 62, cy - 34)], fill=WHITE, width=6)
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out, optimize=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--eyebrow", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    make(a.eyebrow, a.title, a.subtitle, a.out)
    print(a.out)
