"""Make a vertical (1080x1920) text-led video advert from a scene list, in Hourwright's colours and fonts.

No product photography or AI-generated watch imagery is used, so nothing can misrepresent a model.
Each scene: eyebrow (small caps line), headline, optional sub-line. Captions are the content, so the ad
works without sound. Usage:
    python3 scripts/make_ad.py ops/ads/black-friday.json ops/ads/black-friday.mp4
Requires: pillow, fonttools, brotli, ffmpeg.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from make_pin import BG, BRASS, WHITE, GREY, font  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402
import io  # noqa: E402
import urllib.request  # noqa: E402

PRODUCTS = {}


def product(pid):
    """Catalogue entry by id (data/products.json): retailer's own image, name, prices."""
    if not PRODUCTS:
        data = json.loads((pathlib.Path(__file__).parent.parent / "data" / "products.json").read_text())
        PRODUCTS.update({p["id"]: p for p in data["products"]})
    return PRODUCTS[pid]


def product_image(url, box):
    """Retailer's product photo, unaltered apart from scaling, on a soft studio light."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Hourwright ad builder)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        im = Image.open(io.BytesIO(r.read())).convert("RGB")
    im.thumbnail((box, box), Image.LANCZOS)
    return im

W, H, FPS = 1080, 1920, 30


def framed(url, height=640):
    """Retailer photo exactly as supplied (scaled only: Awin/Rakuten licences allow publishing
    Advertiser Materials 'without modification'), mounted in a thin brass frame with a contact shadow."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Hourwright ad builder)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        im = Image.open(io.BytesIO(r.read())).convert("RGB")
    im = im.resize((int(im.width * height / im.height), height), Image.LANCZOS)
    b = 6
    canvas = Image.new("RGBA", (im.width + 2 * b + 120, height + 2 * b + 50), (0, 0, 0, 0))
    sh = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(sh).ellipse((40, height + 2 * b - 8, canvas.width - 40, height + 2 * b + 40), fill=180)
    canvas.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(16)))
    ImageDraw.Draw(canvas).rectangle((60, 0, 60 + im.width + 2 * b - 1, height + 2 * b - 1), fill=(198, 160, 92, 255))
    canvas.paste(im, (60 + b, b))
    return canvas


def cutout(url, height=640):
    """Not used for retailer images unless the programme permits modification. Retailer photo with its plain studio backdrop removed (border-connected flood fill), plus a
    soft contact shadow. The watch itself is untouched apart from scaling."""
    from PIL import ImageChops
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Hourwright ad builder)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        im = Image.open(io.BytesIO(r.read())).convert("RGB")
    bg = im.getpixel((2, 2))
    diff = ImageChops.difference(im, Image.new("RGB", im.size, bg)).split()
    d = ImageChops.lighter(ImageChops.lighter(diff[0], diff[1]), diff[2])
    near = d.point(lambda v: 255 if v < 16 else 0)
    for xy in [(0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1)]:
        if near.getpixel(xy) == 255:
            ImageDraw.floodfill(near, xy, 128)
    alpha = near.point(lambda v: 0 if v == 128 else 255).filter(ImageFilter.GaussianBlur(1.2))
    rgba = im.convert("RGBA"); rgba.putalpha(alpha)
    rgba = rgba.crop(alpha.point(lambda v: 255 if v > 20 else 0).getbbox())
    rgba = rgba.resize((int(rgba.width * height / rgba.height), height), Image.LANCZOS)
    canvas = Image.new("RGBA", (rgba.width + 200, height + 60), (0, 0, 0, 0))
    sh = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(sh).ellipse((60, height + 5, canvas.width - 60, height + 50), fill=170)
    canvas.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)))
    canvas.alpha_composite(rgba, (100, 0))
    return canvas


def hero_overlay(scene, p, path):
    """Text layer for a hero product scene: saving at the top, facts in the lower third."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shade = Image.new("L", (1, H), 0)
    for yy in range(H):
        top = max(0, 190 - yy // 2) if yy < 380 else 0
        bot = max(0, min(215, int((yy - 1100) * 0.4)))
        shade.putpixel((0, yy), max(top, bot))
    im.paste(Image.new("RGBA", (W, H), (6, 16, 13, 255)), (0, 0), shade.resize((W, H)))
    d = ImageDraw.Draw(im)
    def centre(y, t, f, fill):
        d.text(((W - d.textlength(t, font=f)) / 2, y), t, font=f, fill=fill)
    brand = p["brand"].replace("Tag Heuer", "TAG Heuer")
    centre(110, scene.get("eyebrow", "BLACK FRIDAY").upper(), font("hanken-grotesk", 42, 600), BRASS)
    saving = p["was_price"] - p["price"]
    centre(175, scene.get("headline", f"Save £{saving:,.0f}"), font("fraunces", 150, 600), WHITE)
    y = 1330
    name = scene.get("name") or f"{brand} {p['name'].split(' Mens')[0].split(' Ladies')[0]}"
    nf = font("fraunces", 60, 600)
    for line in wrap(d, name, nf, W - 160)[:2]:
        centre(y, line, nf, WHITE); y += 72
    y += 18
    centre(y, f"Was £{p['was_price']:,.0f}   Now £{p['price']:,.0f}", font("hanken-grotesk", 60, 600), BRASS); y += 84
    centre(y, f"at {p['retailer_name']}, UK authorised retailer", font("hanken-grotesk", 40, 400), GREY)
    centre(H - 170, "Hourwright", font("fraunces", 52, 600), WHITE)
    im.save(path)


def wrap(draw, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def frame(scene, path):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    x, y = 96, 560
    if scene.get("product"):
        p = product(scene["product"])
        # Studio card: a light panel with a soft glow, the product photo centred on it.
        glow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(glow).ellipse((90, 170, W - 90, 1070), fill=110)
        glow = glow.filter(ImageFilter.GaussianBlur(120))
        im.paste(Image.new("RGB", (W, H), "#2a5a4d"), (0, 0), glow)
        ph = product_image(p["image"], 800)
        card = Image.new("RGB", (860, 860), ph.getpixel((2, 2)))  # match the photo's own backdrop
        card.paste(ph, ((860 - ph.width) // 2, (860 - ph.height) // 2))
        mask = Image.new("L", card.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 860, 860), 36, fill=255)
        im.paste(card, ((W - 860) // 2, 200), mask)
        y = 1100
        scene.setdefault("eyebrow", p["brand"].replace("Tag Heuer", "TAG Heuer"))
        if scene.get("show_price") and p.get("was_price"):
            scene.setdefault("sub", f"Was £{p['was_price']:,.0f}. Now £{p['price']:,.0f} at {p['retailer_name']}.")
    if scene.get("eyebrow"):
        d.text((x, y), scene["eyebrow"].upper(), font=font("hanken-grotesk", 40, 600), fill=BRASS)
        y += 90
    hf = font("fraunces", scene.get("size", 118), 600)
    for line in wrap(d, scene["headline"], hf, W - 2 * x):
        d.text((x, y), line, font=hf, fill=WHITE)
        y += int(scene.get("size", 118) * 1.08)
    if scene.get("sub"):
        y += 24
        sf = font("hanken-grotesk", 50, 400)
        for line in wrap(d, scene["sub"], sf, W - 2 * x):
            d.text((x, y), line, font=sf, fill=GREY)
            y += 70
    d.text((x, H - 300), "Hourwright", font=font("fraunces", 64, 600), fill=WHITE)
    d.text((x, H - 220), "hourwright.co.uk", font=font("hanken-grotesk", 44, 500), fill=BRASS)
    if scene.get("fine"):
        ff = font("hanken-grotesk", 28, 400)
        yy = H - 150
        for line in textwrap.wrap(scene["fine"], 70):
            d.text((x, yy), line, font=ff, fill=GREY)
            yy += 38
    im.save(path)


def reductions():
    product("x") if False else None
    if not PRODUCTS:
        try:
            product("")
        except KeyError:
            pass
    return sum(1 for p in PRODUCTS.values() if p.get("was_price") and p["was_price"] > p["price"])


def overlay(scene, path):
    """Transparent text layer for a video (b-roll) scene: lower-third headline over a soft shade."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shade = Image.new("L", (1, H), 0)
    for yy in range(H):
        shade.putpixel((0, yy), max(0, min(200, int((yy - 950) * 0.35))))
    im.paste(Image.new("RGBA", (W, H), (8, 20, 17, 255)), (0, 0), shade.resize((W, H)))
    d = ImageDraw.Draw(im)
    x, y = 96, scene.get("text_y", 1240)
    if scene.get("eyebrow"):
        d.text((x, y), scene["eyebrow"].upper(), font=font("hanken-grotesk", 40, 600), fill=BRASS)
        y += 90
    if scene.get("headline"):
        hf = font("fraunces", scene.get("size", 118), 600)
        for line in wrap(d, scene["headline"], hf, W - 2 * x):
            d.text((x, y), line, font=hf, fill=WHITE)
            y += int(scene.get("size", 118) * 1.08)
    if scene.get("sub"):
        y += 24
        sf = font("hanken-grotesk", 50, 400)
        for line in wrap(d, scene["sub"], sf, W - 2 * x):
            d.text((x, y), line, font=sf, fill=GREY)
            y += 70
    d.text((x, H - 220), "Hourwright", font=font("fraunces", 56, 600), fill=WHITE)
    im.save(path)


def main(spec_path, out_path):
    spec = json.loads(pathlib.Path(spec_path).read_text())
    tmp = pathlib.Path(tempfile.mkdtemp())
    inputs, filters, n = [], [], len(spec["scenes"])
    k = 0  # ffmpeg input index
    for i, s in enumerate(spec["scenes"]):
        for key in ("headline", "sub", "eyebrow"):
            if "{reductions}" in s.get(key, ""):
                s[key] = s[key].replace("{reductions}", str(reductions()))
        dur = s.get("seconds", 3)
        frames = int(dur * FPS)
        fades = f"fade=t=in:st=0:d=0.35,fade=t=out:st={dur - 0.35}:d=0.35"
        if s.get("hero"):
            p = product(s["hero"])
            c = tmp / f"c{i}.png"
            (cutout if s.get("cutout_permitted") else framed)(p["image"], s.get("watch_height", 600)).save(c)
            o = tmp / f"o{i}.png"; hero_overlay(s, p, o)
            speed = s.get("speed", 0.7)
            base = s.get("base_y", 1060)
            inputs += ["-ss", str(s.get("from", 0)), "-t", str(dur * speed), "-i", s.get("bg", "assets/studio-plinth-1.mp4"),
                       "-loop", "1", "-t", str(dur), "-i", str(c), "-loop", "1", "-t", str(dur), "-i", str(o)]
            filters.append(f"[{k}:v]setpts=(PTS-STARTPTS)/{speed},scale={W}:{H}:force_original_aspect_ratio=increase,"
                           f"crop={W}:{H},fps={FPS},trim=duration={dur},setsar=1[b{i}];"
                           f"[{k + 1}:v]format=rgba,scale=w='iw*(0.88+0.12*min(t/{dur},1))':h=-1:eval=frame,"
                           f"fade=t=in:st=0.1:d=0.7:alpha=1[w{i}];"
                           f"[b{i}][w{i}]overlay=x=(W-w)/2:y={base}-h:shortest=1[bw{i}];"
                           f"[bw{i}][{k + 2}:v]overlay=0:0,format=yuv420p,{fades}[v{i}]")
            k += 3
            continue
        if s.get("video"):
            speed = s.get("speed", 1.0)
            o = tmp / f"o{i}.png"
            overlay(s, o)
            inputs += ["-ss", str(s.get("from", 0)), "-t", str(dur * speed), "-i", s["video"], "-loop", "1", "-t", str(dur), "-i", str(o)]
            filters.append(f"[{k}:v]setpts=(PTS-STARTPTS)/{speed},scale={W}:{H}:force_original_aspect_ratio=increase,"
                           f"crop={W}:{H},fps={FPS},trim=duration={dur},setsar=1[b{i}];"
                           f"[b{i}][{k + 1}:v]overlay=0:0,format=yuv420p,{fades}[v{i}]")
            k += 2
            continue
        p = tmp / f"s{i}.png"
        frame(s, p)
        inputs += ["-i", str(p)]
        filters.append(f"[{k}:v]scale={W * 2}:{H * 2},zoompan=z='min(1+0.06*on/{frames},1.06)':x='iw/2-(iw/zoom/2)':"
                       f"y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p,setsar=1,{fades}[v{i}]")
        k += 1
    filters.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[out]")
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    audio = [a for a in spec.get("audio", []) if pathlib.Path(a["file"]).exists()]
    for a in audio:
        inputs += ["-i", a["file"]]
    amap = []
    if audio:
        parts = [f"[{k + j}:a]volume={a.get('volume', 1.0)},adelay={int(a.get('start', 0) * 1000)}|{int(a.get('start', 0) * 1000)}[a{j}]"
                 for j, a in enumerate(audio)]
        total = sum(s.get("seconds", 3) for s in spec["scenes"])
        filters += parts + ["".join(f"[a{j}]" for j in range(len(audio))) +
                            f"amix=inputs={len(audio)}:normalize=0,afade=t=out:st={total - 1.2}:d=1.2,atrim=0:{total}[aout]"]
        amap = ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
                    *amap, "-map", "[out]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-movflags", "+faststart",
                    "-pix_fmt", "yuv420p", out_path], check=True)
    # Thumbnail of the first scene for checking and for platforms that ask for a cover.
    first = next((x for x in spec["scenes"] if not x.get("video") and not x.get("hero")), None)
    if first:
        frame(first, pathlib.Path(out_path).with_suffix(".png"))
    print("wrote", out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
