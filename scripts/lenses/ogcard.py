"""1200x630 link-preview cards (og:image), drawn with Pillow in the site's
dark visual language. render_card returns PNG bytes (pure given its inputs;
fonts are read from the repo's bundled assets/fonts). Card failure is the
caller's problem to isolate — these functions just raise."""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = "#0A0E14"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
FAINT = "#76879E"
BORDER = "#1E293B"
STATUS_COLORS = {"ok": "#34D399", "watch": "#FBBF24", "elevated": "#FB923C",
                 "alert": "#F87171", "neutral": "#38BDF8"}

_FONT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"


def _font(size, weight="regular"):
    name = "Inter-SemiBold.ttf" if weight == "semibold" else "Inter-Regular.ttf"
    return ImageFont.truetype(str(_FONT_DIR / name), size)


def _wrap(draw, text, font, max_width):
    """Greedy word wrap by rendered width."""
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and draw.textlength(trial, font=font) > max_width:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def render_card(status, sentence, date_label):
    """The daily verdict card: wordmark, date, status pill, wrapped sentence."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    margin = 80

    # header: wordmark left, date right
    d.text((margin, 64), "BAILEY ANALYTICS", font=_font(34, "semibold"), fill=TEXT)
    date_font = _font(28)
    d.text((W - margin - d.textlength(date_label, font=date_font), 68),
           date_label, font=date_font, fill=MUTED)
    d.line([(margin, 130), (W - margin, 130)], fill=BORDER, width=2)

    # status pill
    color = STATUS_COLORS.get(status, FAINT)
    pill_font = _font(30, "semibold")
    label = status.upper()
    tw = d.textlength(label, font=pill_font)
    px, py, pad_x, pad_y = margin, 180, 28, 12
    d.rounded_rectangle([px, py, px + tw + 2 * pad_x, py + 30 + 2 * pad_y],
                        radius=28, outline=color, width=3)
    d.text((px + pad_x, py + pad_y - 2), label, font=pill_font, fill=color)

    # verdict sentence: shrink until it fits in 4 lines
    max_w = W - 2 * margin
    for size in (54, 48, 42, 36):
        body_font = _font(size, "semibold")
        lines = _wrap(d, sentence, body_font, max_w)
        if len(lines) <= 4:
            break
    y = 290
    for line in lines[:4]:
        d.text((margin, y), line, font=body_font, fill=TEXT)
        y += int(size * 1.35)

    # footer
    d.text((margin, H - 80), "baileyanalytics.com — Today's Brief",
           font=_font(26), fill=FAINT)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_site_card():
    """One-time static brand card for non-brief pages."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    margin = 80
    d.text((margin, 200), "Bailey Analytics", font=_font(72, "semibold"), fill=TEXT)
    tagline = "Daily, plain-English dashboards on the U.S. and global economy"
    for i, line in enumerate(_wrap(d, tagline, _font(34), W - 2 * margin)):
        d.text((margin, 320 + i * 48), line, font=_font(34), fill=MUTED)
    d.text((margin, H - 80), "baileyanalytics.com", font=_font(26), fill=FAINT)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
