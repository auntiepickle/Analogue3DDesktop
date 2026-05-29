#!/usr/bin/env python3
"""Generate the app icon: a gold rounded-square with three traffic-light dots
over a bold "3D". Each size is rendered natively (4x supersample -> LANCZOS) so
small sizes stay crisp AND keep the dots, instead of being downscaled from one
busy 256px master (which looked blocky in the title bar / taskbar).

    python make_icon.py    # writes assets/icon.ico, assets/icon.png, assets/icon.icns

The .icns is the macOS app-bundle icon. It's written with Pillow; if Pillow's
ICNS encoder isn't available, the .iconset/ folder of PNGs is still written so a
Mac can finish the job with:  iconutil -c icns assets/icon.iconset -o assets/icon.icns
"""

import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
SIZES = [16, 24, 32, 48, 64, 128, 256]
# macOS icons go up to 1024 (512@2x) for crisp Retina rendering.
ICNS_SIZES = [16, 32, 64, 128, 256, 512, 1024]

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


def _write_iconset(icns_imgs):
    """Write assets/icon.iconset/ with Apple's required filenames, so a Mac can
    run `iconutil -c icns assets/icon.iconset -o assets/icon.icns` if needed."""
    iconset = os.path.join(ASSETS, "icon.iconset")
    os.makedirs(iconset, exist_ok=True)
    # (pixel size, Apple label) - @2x entries reuse the doubled-size render.
    pairs = [(16, "16x16"), (32, "16x16@2x"), (32, "32x32"), (64, "32x32@2x"),
             (128, "128x128"), (256, "128x128@2x"), (256, "256x256"),
             (512, "256x256@2x"), (512, "512x512"), (1024, "512x512@2x")]
    for px, label in pairs:
        icns_imgs[px].save(os.path.join(iconset, f"icon_{label}.png"))
    return iconset


def main():
    imgs = [render(s) for s in SIZES]
    ico_path = os.path.join(ASSETS, "icon.ico")
    imgs[-1].save(ico_path, format="ICO",
                  sizes=[(s, s) for s in SIZES], append_images=imgs[:-1])
    imgs[-1].save(os.path.join(ASSETS, "icon.png"))
    print("wrote", ico_path, "sizes:", SIZES)

    # macOS app-bundle icon. Always write the .iconset (iconutil fallback); try
    # the Pillow ICNS encoder for a ready-to-use assets/icon.icns.
    icns_imgs = {s: render(s) for s in ICNS_SIZES}
    _write_iconset(icns_imgs)
    icns_path = os.path.join(ASSETS, "icon.icns")
    try:
        icns_imgs[1024].save(icns_path, format="ICNS")
        print("wrote", icns_path)
    except Exception as e:
        print(f"could not write .icns via Pillow ({e}); on a Mac run:")
        print("  iconutil -c icns assets/icon.iconset -o assets/icon.icns")


if __name__ == "__main__":
    main()
