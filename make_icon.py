#!/usr/bin/env python3
"""Generate the app icon: a gold rounded-square with three traffic-light dots
over a bold "3D". Each size is rendered natively (4x supersample -> LANCZOS) so
small sizes stay crisp AND keep the dots, instead of being downscaled from one
busy 256px master (which looked blocky in the title bar / taskbar).

    python make_icon.py    # writes assets/icon.ico (+ assets/icon.png)
"""

import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
SIZES = [16, 24, 32, 48, 64, 128, 256]

GOLD = (244, 205, 1, 255)
DARK = (12, 12, 14, 255)
DOTS = [(255, 95, 86, 255), (245, 197, 66, 255), (61, 220, 132, 255)]  # red, gold, green

_FONTS = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _font(px):
    for p in _FONTS:
        if os.path.isfile(p):
            return ImageFont.truetype(p, px)
    return ImageFont.load_default()


def render(size):
    ss = size * 4  # supersample for smooth edges at the final size
    img = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    m = round(ss * 0.055)
    bt = max(2, round(ss * 0.075))
    r = round(ss * 0.20)
    d.rounded_rectangle([m, m, ss - 1 - m, ss - 1 - m], radius=r,
                        fill=DARK, outline=GOLD, width=bt)

    dr = round(ss * 0.062)
    cy = round(ss * 0.33)
    for cx_frac, color in zip((0.34, 0.50, 0.66), DOTS):
        cx = round(ss * cx_frac)
        d.ellipse([cx - dr, cy - dr, cx + dr, cy + dr], fill=color)

    f = _font(round(ss * 0.42))
    text = "3D"
    box = d.textbbox((0, 0), text, font=f)
    tw, th = box[2] - box[0], box[3] - box[1]
    tx = (ss - tw) / 2 - box[0]
    ty = round(ss * 0.50) - box[1]
    d.text((tx, ty), text, font=f, fill=GOLD)

    return img.resize((size, size), Image.LANCZOS)


def main():
    imgs = [render(s) for s in SIZES]
    ico_path = os.path.join(ASSETS, "icon.ico")
    imgs[-1].save(ico_path, format="ICO",
                  sizes=[(s, s) for s in SIZES], append_images=imgs[:-1])
    imgs[-1].save(os.path.join(ASSETS, "icon.png"))
    print("wrote", ico_path, "sizes:", SIZES)


if __name__ == "__main__":
    main()
