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


def main(spec_path, out_path):
    spec = json.loads(pathlib.Path(spec_path).read_text())
    tmp = pathlib.Path(tempfile.mkdtemp())
    inputs, filters, n = [], [], len(spec["scenes"])
    for i, s in enumerate(spec["scenes"]):
        p = tmp / f"s{i}.png"
        frame(s, p)
        inputs += ["-i", str(p)]
        dur = s.get("seconds", 3)
        frames = int(dur * FPS)
        filters.append(f"[{i}:v]scale={W * 2}:{H * 2},zoompan=z='min(1+0.06*on/{frames},1.06)':x='iw/2-(iw/zoom/2)':"
                       f"y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p,"
                       f"fade=t=in:st=0:d=0.35,fade=t=out:st={dur - 0.35}:d=0.35[v{i}]")
    filters.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[out]")
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    audio = [a for a in spec.get("audio", []) if pathlib.Path(a["file"]).exists()]
    for a in audio:
        inputs += ["-i", a["file"]]
    amap = []
    if audio:
        parts = [f"[{n + j}:a]volume={a.get('volume', 1.0)},adelay={int(a.get('start', 0) * 1000)}|{int(a.get('start', 0) * 1000)}[a{j}]"
                 for j, a in enumerate(audio)]
        total = sum(s.get("seconds", 3) for s in spec["scenes"])
        filters += parts + ["".join(f"[a{j}]" for j in range(len(audio))) +
                            f"amix=inputs={len(audio)}:normalize=0,afade=t=out:st={total - 1.2}:d=1.2,atrim=0:{total}[aout]"]
        amap = ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
                    *amap, "-map", "[out]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-movflags", "+faststart",
                    "-pix_fmt", "yuv420p", out_path], check=True)
    # Thumbnail of the first scene for checking and for platforms that ask for a cover.
    frame(spec["scenes"][0], pathlib.Path(out_path).with_suffix(".png"))
    print("wrote", out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
