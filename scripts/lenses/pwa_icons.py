"""Generate PWA app icons from the favicon design (rounded #0F172A panel +
#38BDF8 chart line). Mirrors ogcard.py's Pillow usage. Static assets — run once
and commit; not part of the daily refresh."""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = (15, 23, 42, 255)    # #0F172A
BLUE = (56, 189, 248, 255)   # #38BDF8
PTS64 = [(10, 44), (22, 34), (32, 38), (44, 20), (54, 26)]  # favicon polyline, 64-space


def _draw(size, maskable=False):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    inset = size * 0.10 if maskable else 0          # maskable safe zone (~80% art)
    s = (size - 2 * inset) / 64.0

    def P(p):
        return (inset + p[0] * s, inset + p[1] * s)

    if maskable:
        d.rectangle([0, 0, size, size], fill=PANEL)  # full-bleed bg for the mask
    else:
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=14 * (size / 64.0), fill=PANEL)
    w = max(2, int(round(5.5 * s)))
    line = [P(p) for p in PTS64]
    d.line(line, fill=BLUE, width=w, joint="curve")
    r = w / 2.0
    for x, y in line:                                # round caps/joins
        d.ellipse([x - r, y - r, x + r, y + r], fill=BLUE)
    return img


def generate(root=None):
    root = root or ROOT
    (root / "icons").mkdir(parents=True, exist_ok=True)
    out = []
    for rel, size, mask in [
        ("icons/icon-192.png", 192, False),
        ("icons/icon-512.png", 512, False),
        ("icons/icon-192-maskable.png", 192, True),
        ("icons/icon-512-maskable.png", 512, True),
    ]:
        _draw(size, maskable=mask).save(root / rel)
        out.append(rel)
    _draw(180, maskable=False).convert("RGB").save(root / "apple-touch-icon.png")  # opaque
    out.append("apple-touch-icon.png")
    return out


if __name__ == "__main__":
    print(generate())
