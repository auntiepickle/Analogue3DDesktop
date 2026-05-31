"""Fake test data for the Desktop app, activated when A3D_DEMO=1.

Pretends ~120 N64 games + plenty of save states + snapshots + backups so we can
iterate on the design at real density instead of the 3-game default state. No SD
card required; methods that would talk to hardware return canned data.
"""

import os
import hashlib
import random
from datetime import datetime, timedelta

# Verified cart_id -> game name pairs from the cached community labels.db.
# Each pair was hand-identified by dumping the cart art and recognizing the
# cover. Using these first means the demo gallery/memories show titles that
# actually MATCH the cart art beside them. Order = stable demo display order.
VERIFIED_TITLES = [
    ("03cc04ee", "Mario Kart 64"),
    ("04079b93", "Super Smash Bros."),
    ("025b1beb", "Mario Party"),
    ("0071a6de", "The Legend of Zelda: Majora's Mask"),
    ("10cf7be3", "GoldenEye 007"),
    ("02e906a1", "Mega Man 64"),
    ("0fa0615b", "Mortal Kombat Trilogy"),
    ("0079994a", "Turok: Rage Wars"),
    ("088ca0db", "Madden NFL '99"),
    ("003965ca", "NFL Quarterback Club 99"),
    ("0498e26e", "NFL Quarterback Club 2001"),
    ("04fb8b29", "All-Star Baseball 2000"),
    ("0149b304", "Nagano Winter Olympics '98"),
    ("03aaa5d7", "Carmageddon 64"),
    ("005574c0", "Armorines: Project S.W.A.R.M."),
    ("09708fb9", "BattleTanx: Global Assault"),
    ("0720286c", "Bust-A-Move 2: Arcade Edition"),
    ("06b608c0", "Telefoot Soccer 2000"),
]

# Well-known N64 titles - mix of hits, RPGs, sports, racing, weird stuff -
# enough breadth that the gallery and memories list feel like a real library.
# Order: verified-art titles first (so the visible-first tiles always match
# their art), then the curated extras for breadth.
_EXTRA_TITLES = [
    "Super Mario 64", "The Legend of Zelda: Ocarina of Time",
    "Star Fox 64", "Banjo-Kazooie", "Banjo-Tooie",
    "Conker's Bad Fur Day", "Perfect Dark", "Donkey Kong 64", "Paper Mario",
    "Mario Tennis", "Mario Golf", "Mario Party 2", "Mario Party 3",
    "Yoshi's Story", "Diddy Kong Racing", "1080 Snowboarding",
    "Excitebike 64", "Wave Race 64", "Pokemon Snap", "Pokemon Stadium",
    "Pokemon Stadium 2", "Pokemon Puzzle League", "F-Zero X",
    "Star Wars: Rogue Squadron", "Star Wars: Shadows of the Empire",
    "Star Wars Episode I: Racer", "Resident Evil 2",
    "Rayman 2: The Great Escape", "Turok: Dinosaur Hunter",
    "Turok 2: Seeds of Evil", "Turok 3: Shadow of Oblivion",
    "Mortal Kombat 4", "WWF No Mercy", "WWF WrestleMania 2000",
    "Tony Hawk's Pro Skater", "Tony Hawk's Pro Skater 2",
    "Tony Hawk's Pro Skater 3", "WCW/nWo Revenge", "WCW/nWo World Tour",
    "Snowboard Kids", "Snowboard Kids 2", "Bomberman 64", "Bomberman Hero",
    "Bomberman 64: The Second Attack", "Kirby 64: The Crystal Shards",
    "Killer Instinct Gold", "Cruisin USA", "Cruisin World", "Cruisin Exotica",
    "San Francisco Rush", "Rush 2: Extreme Racing", "F-1 World Grand Prix",
    "Beetle Adventure Racing", "Top Gear Rally", "Hydro Thunder", "Roadsters",
    "World Driver Championship", "NFL Blitz", "NFL Blitz 2000", "NBA Hangtime",
    "NBA Jam 99", "NBA Showtime: NBA on NBC", "NHL Breakaway 98", "NHL 99",
    "All-Star Baseball 2001", "Triple Play 2000",
    "Tetrisphere", "Wetrix", "Quake", "Quake II", "Quake 64", "Hexen",
    "Doom 64", "Castlevania", "Castlevania: Legacy of Darkness",
    "ISS 64", "ISS Pro 98", "ISS 2000", "Worms Armageddon", "Mickey's Speedway USA",
    "Magical Tetris Challenge", "Tetris 64", "Glover", "Earthworm Jim 3D",
    "Rampage World Tour", "Mischief Makers", "Hybrid Heaven", "Penny Racers",
    "Chameleon Twist", "Chameleon Twist 2", "Dr. Mario 64",
    "Hey You, Pikachu", "Hot Wheels Turbo Racing", "Off Road Challenge",
    "Test Drive 64", "Vigilante 8", "Vigilante 8: Second Offense",
    "Twisted Edge Snowboarding", "South Park", "South Park Rally", "Quest 64",
    "Aidyn Chronicles", "Body Harvest", "Spider-Man",
    "Battletanx", "Forsaken 64", "Daikatana",
    "Aero Fighters Assault", "Wipeout 64", "Extreme-G", "Extreme-G 2",
    "Indy Racing 2000", "Madden NFL 2000",
    "Pilotwings 64", "Blast Corps", "Sin and Punishment",
    "Ridge Racer 64", "Mace: The Dark Age", "California Speed",
    "Knife Edge: Nose Gunner", "Ogre Battle 64",
]
GAMES = [t for _, t in VERIFIED_TITLES] + _EXTRA_TITLES


def _cart_id_hash(title):
    """Fallback deterministic 8-char hex from title, when no real labels.db is around."""
    return hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]


# ---- real labels.db integration ----
# When the engine has the community labels.db cached (or can download it), we
# use REAL N64 cart IDs from that db as our demo cart_ids. cart_art() then
# returns the actual RetroGameCorps box art per cart - far better than a
# generated SVG placeholder. Titles are still drawn from our curated GAMES
# list; the title-to-cart-id pairing is deterministic but arbitrary - we're
# trading "exact pairing" for "real art shows up in the gallery."

_REAL_DB_PATH = None
_REAL_CART_IDS = None
_CART_ID_BY_TITLE = None


def _real_db_path():
    """Ensure (and return) the community labels.db path, downloading if needed."""
    global _REAL_DB_PATH
    if _REAL_DB_PATH is not None:
        return _REAL_DB_PATH or None
    try:
        from analogue3d import labels
        p = labels.community_cache() or labels.community_db()
        _REAL_DB_PATH = p if p and os.path.isfile(p) else ""
    except Exception:
        _REAL_DB_PATH = ""
    return _REAL_DB_PATH or None


def _real_cart_ids():
    """Parse cart IDs straight from the labels.db binary (engine doesn't expose
    a public iterator). Header 256 bytes; uint32-LE sorted ID table at 0x100;
    0xFFFFFFFF-terminated; max 4096."""
    global _REAL_CART_IDS
    if _REAL_CART_IDS is not None:
        return _REAL_CART_IDS
    path = _real_db_path()
    if not path:
        _REAL_CART_IDS = []
        return _REAL_CART_IDS
    import struct
    try:
        with open(path, "rb") as f:
            f.seek(0x100)
            tbl = f.read(4096 * 4)
        ids = []
        for i in range(0, len(tbl), 4):
            v = struct.unpack_from("<I", tbl, i)[0]
            if v == 0xFFFFFFFF:
                break
            ids.append(f"{v:08x}")
        _REAL_CART_IDS = ids
    except Exception:
        _REAL_CART_IDS = []
    return _REAL_CART_IDS


_VERIFIED_BY_TITLE = {t: cid for cid, t in VERIFIED_TITLES}


def _cart_id(title):
    """Deterministic title -> real labels.db cart_id. VERIFIED_TITLES gives us
    correct pairings for the popular titles; the rest fall through to arbitrary
    real cart_ids (so they still get real art, just not matching art) or the
    hash fallback if labels.db isn't around."""
    if title in _VERIFIED_BY_TITLE:
        return _VERIFIED_BY_TITLE[title]
    global _CART_ID_BY_TITLE
    if _CART_ID_BY_TITLE is None:
        _CART_ID_BY_TITLE = {}
        real = _real_cart_ids()
        if real:
            verified_set = {cid for cid, _ in VERIFIED_TITLES}
            unused = [r for r in real if r not in verified_set]
            for i, t in enumerate(_EXTRA_TITLES):
                _CART_ID_BY_TITLE[t] = unused[i % len(unused)] if unused else real[i % len(real)]
    cid = _CART_ID_BY_TITLE.get(title)
    return cid if cid else _cart_id_hash(title)


def _rng(seed):
    return random.Random(seed)


def detect():
    # Use a realistic Windows drive-letter path so demo screenshots look like
    # what a user actually sees in prod — not the fake "DEMO://" protocol.
    return {
        "cards": [{
            "path": "E:\\",
            "label": "ANALOGUE 3D",
            "free_gb": 14,
            "strong": True,
            "reasons": ["demo mode"],
        }],
        "controllers": 1,
    }


def list_backups():
    out = []
    now = datetime.now()
    days_ago = [0, 0, 1, 2, 5, 9, 14, 21, 30]
    labels_by_day = {0: "before-firmware", 2: "before-art-pack", 14: "before-Auto"}
    for i, d in enumerate(days_ago):
        ts = now - timedelta(days=d, hours=(i * 3) % 12)
        when = ts.strftime("%Y-%m-%d %H:%M")
        label = labels_by_day.get(d, "")
        tag = "_" + label if label else ""
        name = f"analogue3d_backup_{ts.strftime('%Y-%m-%d_%H-%M-%S')}{tag}.zip"
        out.append({
            "name": name,
            "bytes": 80 * 1024 * 1024 + _rng(name).randint(0, 12 * 1024 * 1024),
            "when": when,
            "label": label,
        })
    return out


def list_memories(root):
    games = []
    now = datetime.now()
    for title in GAMES:
        r = _rng(title)
        # weight low counts more heavily so the demo looks like a real card
        n_states = r.choices(
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12],
            weights=[12, 18, 14, 14, 10, 8, 6, 5, 4, 3, 6]
        )[0]
        if n_states == 0:
            continue
        cart_id = _cart_id(title)
        states = []
        for i in range(n_states):
            ts = now - timedelta(days=r.randint(0, 90), seconds=r.randint(0, 86400))
            states.append({
                "name": f"{i:03d}.SAV",
                "when": ts.strftime("%Y-%m-%d %H:%M"),
                "bytes": r.randint(32 * 1024, 256 * 1024),
            })
        games.append({
            "title": title,
            "cart_id": cart_id,
            "folder": cart_id,
            "count": n_states,
            "total_bytes": sum(s["bytes"] for s in states),
            "states": states,
        })
    return {"available": True, "keep_default": 5, "games": games}


def list_snapshots():
    out = []
    now = datetime.now()
    snapshots = [
        (1, ""),
        (3, "before-trip"),
        (8, "weekend"),
        (15, "My-Favs"),
        (28, ""),
    ]
    for days_ago, lbl in snapshots:
        ts = now - timedelta(days=days_ago)
        tag = "_" + lbl if lbl else ""
        name = f"snapshot_{ts.strftime('%Y-%m-%d_%H-%M-%S')}{tag}.zip"
        when = ts.strftime("%Y-%m-%d %H:%M")
        if lbl:
            when += "  ·  " + lbl
        r = _rng(name)
        n_games = r.randint(10, 30)
        games = [{"title": g, "count": r.randint(1, 6)} for g in r.sample(GAMES, n_games)]
        out.append({
            "name": name, "when": when, "label": lbl,
            "bytes": r.randint(60, 250) * 1024 * 1024,
            "count": sum(g["count"] for g in games),
            "games": games,
        })
    return out


def cart_art_games(root, source=None):
    items = []
    for title in sorted(GAMES, key=lambda t: t.lower()):
        items.append({
            "cart_id": _cart_id(title),
            "title": title,
            "overridden": False,
        })
    return {"db_present": True, "games": items}


# Map cart_id back to title (lazy so _cart_id() finishes wiring first).
_TITLE_BY_ID = None
def _title_by_id(cid):
    global _TITLE_BY_ID
    if _TITLE_BY_ID is None:
        _TITLE_BY_ID = {_cart_id(t): t for t in GAMES}
    return _TITLE_BY_ID.get(cid, "UNKNOWN")


def cart_art(cart_id):
    """Demo cart-art: prefer REAL labels.db image for this cart_id (when the
    engine has the community pack cached, our demo IDs come from labels.db too
    so the lookup actually hits). Falls back to a stylized SVG otherwise."""
    # 1) Try real labels.db image (RetroGameCorps community pack).
    path = _real_db_path()
    if path:
        try:
            from analogue3d import labels
            img = labels.read_label_image(path, cart_id)
            if img is not None:
                import io as _io, base64 as _b64
                buf = _io.BytesIO()
                img.convert("RGB").save(buf, "PNG")
                return "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:
            pass
    # 2) Generated SVG fallback for cart_ids without a labels.db entry.
    import base64 as b64
    title = _title_by_id(cart_id)
    h = int(cart_id, 16)
    hue1 = h % 360
    hue2 = (h // 256) % 360
    sat1 = 55 + (h // 65536) % 25      # 55-80
    safe = (title.split(":")[0]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Break long titles roughly in half on the nearest space
    if len(safe) > 14:
        mid = len(safe) // 2
        space = safe.rfind(" ", 0, mid + 6)
        if space != -1:
            line1, line2 = safe[:space], safe[space + 1:]
        else:
            line1, line2 = safe[:14], safe[14:]
    else:
        line1, line2 = safe, ""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 240" preserveAspectRatio="xMidYMid slice">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="hsl({hue1},{sat1}%,28%)"/>'
        f'<stop offset="1" stop-color="hsl({hue2},{sat1 - 15}%,12%)"/>'
        f'</linearGradient></defs>'
        '<rect width="200" height="240" fill="url(#g)"/>'
        '<rect x="6" y="6" width="188" height="228" fill="none" stroke="rgba(255,255,255,.18)" stroke-width="1"/>'
        '<text x="100" y="32" font-family="Verdana,Arial,sans-serif" font-size="9" font-weight="700" '
        'fill="rgba(255,255,255,.65)" text-anchor="middle" letter-spacing="2.5">NINTENDO 64</text>'
        f'<text x="100" y="135" font-family="Verdana,Arial,sans-serif" font-size="15" font-weight="700" '
        f'fill="white" text-anchor="middle">{line1}</text>'
        + (f'<text x="100" y="156" font-family="Verdana,Arial,sans-serif" font-size="15" font-weight="700" '
           f'fill="white" text-anchor="middle">{line2}</text>' if line2 else '')
        + '<rect x="62" y="195" width="76" height="22" fill="rgba(0,0,0,.4)" '
          'stroke="rgba(255,255,255,.35)" stroke-width="1"/>'
          '<text x="100" y="210" font-family="Verdana,Arial,sans-serif" font-size="8" '
          'fill="rgba(255,255,255,.8)" text-anchor="middle" letter-spacing="2">ESRB E</text>'
        + '</svg>'
    )
    return "data:image/svg+xml;base64," + b64.b64encode(svg.encode("utf-8")).decode("ascii")


def memory_thumbnail(root, folder, name):
    """Save-state preview thumbnail. The Analogue 3D itself stores a captured
    gameplay frame inside each .SAV; in demo mode we don't have those, so we
    return a darkened/letterboxed cart-art derivative as a stand-in. Better
    than the bare black square the UI shows otherwise. The folder value is
    the cart_id (we set it that way in list_memories)."""
    # 1) Try real cart art for the cart_id, render as a "save-state-like" frame.
    path = _real_db_path()
    if path:
        try:
            from analogue3d import labels
            img = labels.read_label_image(path, folder)
            if img is not None:
                import io as _io, base64 as _b64
                from PIL import Image, ImageDraw, ImageEnhance
                # Letterbox to a 16:9-ish save-state aspect, dim a touch, badge it.
                w, h = 320, 200
                frame = Image.new("RGB", (w, h), (8, 8, 10))
                src = img.convert("RGB")
                # Cover-fit
                sw, sh = src.size
                scale = max(w / sw, h / sh)
                nw, nh = int(sw * scale), int(sh * scale)
                src = src.resize((nw, nh))
                frame.paste(src, ((w - nw) // 2, (h - nh) // 2))
                # Slight darken + a thin scanline overlay to read as "frame capture".
                frame = ImageEnhance.Brightness(frame).enhance(0.75)
                ovl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                d = ImageDraw.Draw(ovl)
                for y in range(0, h, 3):
                    d.line([(0, y), (w, y)], fill=(0, 0, 0, 36))
                frame = Image.alpha_composite(frame.convert("RGBA"), ovl).convert("RGB")
                # State number in the corner derived from filename.
                num = "".join(c for c in (name or "") if c.isdigit())[:3] or "001"
                d2 = ImageDraw.Draw(frame)
                d2.text((8, h - 18), f"STATE {num}", fill=(220, 220, 220))
                buf = _io.BytesIO()
                frame.save(buf, "JPEG", quality=72)
                return "data:image/jpeg;base64," + _b64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:
            pass
    # 2) Fallback: empty string (UI shows blank, current behavior).
    return ""


def versions(root):
    return {
        "console_current": "1.3.0", "console_latest": "1.3.0",
        "console_update": False, "controllers": 1,
        "ctrl_current": "2.04", "ctrl_latest": "2.04", "ctrl_update": False,
    }


def controller_versions():
    return {"ok": True, "versions": [
        {"version_int": 0x0204, "label": "2.04"},
        {"version_int": 0x0203, "label": "2.03"},
        {"version_int": 0x0202, "label": "2.02"},
        {"version_int": 0x0201, "label": "2.01"},
        {"version_int": 0x0200, "label": "2.00"},
    ]}
