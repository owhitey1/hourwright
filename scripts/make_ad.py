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
from PIL import Image, ImageDraw  # noqa: E402

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
    if scene.get("eyebrow"):
        d.text((x, y), scene["eyebrow"].upper(), font=font("hanken-grotesk", 40, 600), fill=BRASS)
        y += 90
    hf = font("fraunces", scene.get("size", 118), 600)
    for line in wrap(d, scene["headline"], hf, W - 2 * x):
        d.text((x, y), line, font=hf, fill=WHITE)
        y += int(scene.get("size", 118) * 1.12)
    if scene.get("sub"):
        y += 40
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
        inputs += ["-loop", "1", "-t", str(s.get("seconds", 3)), "-i", str(p)]
        dur = s.get("seconds", 3)
        filters.append(f"[{i}:v]fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.3,fade=t=out:st={dur - 0.3}:d=0.3[v{i}]")
    filters.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[out]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
                    "-map", "[out]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-movflags", "+faststart",
                    "-pix_fmt", "yuv420p", out_path], check=True)
    # Thumbnail of the first scene for checking and for platforms that ask for a cover.
    frame(spec["scenes"][0], pathlib.Path(out_path).with_suffix(".png"))
    print("wrote", out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
