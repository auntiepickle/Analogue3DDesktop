"""Fake test data for the Desktop app, activated when A3D_DEMO=1.

Pretends ~120 N64 games + plenty of save states + snapshots + backups so we can
iterate on the design at real density instead of the 3-game default state. No SD
card required; methods that would talk to hardware return canned data.
"""

import hashlib
import random
from datetime import datetime, timedelta

# Well-known N64 titles - mix of hits, RPGs, sports, racing, weird stuff -
# enough breadth that the gallery and memories list feel like a real library.
GAMES = [
    "Super Mario 64", "The Legend of Zelda: Ocarina of Time", "GoldenEye 007",
    "Star Fox 64", "Mario Kart 64", "Banjo-Kazooie", "Banjo-Tooie",
    "Conker's Bad Fur Day", "Perfect Dark", "Donkey Kong 64", "Paper Mario",
    "Super Smash Bros.", "Mario Tennis", "Mario Golf", "Mario Party",
    "Mario Party 2", "Mario Party 3", "Yoshi's Story", "Diddy Kong Racing",
    "1080 Snowboarding", "Excitebike 64", "Wave Race 64", "Pokemon Snap",
    "Pokemon Stadium", "Pokemon Stadium 2", "Pokemon Puzzle League",
    "The Legend of Zelda: Majora's Mask", "F-Zero X", "Star Wars: Rogue Squadron",
    "Star Wars: Shadows of the Empire", "Star Wars Episode I: Racer",
    "Resident Evil 2", "Rayman 2: The Great Escape", "Turok: Dinosaur Hunter",
    "Turok 2: Seeds of Evil", "Turok 3: Shadow of Oblivion", "Turok: Rage Wars",
    "Mortal Kombat Trilogy", "Mortal Kombat 4", "WWF No Mercy",
    "WWF WrestleMania 2000", "Tony Hawk's Pro Skater", "Tony Hawk's Pro Skater 2",
    "Tony Hawk's Pro Skater 3", "WCW/nWo Revenge", "WCW/nWo World Tour",
    "Snowboard Kids", "Snowboard Kids 2", "Bomberman 64", "Bomberman Hero",
    "Bomberman 64: The Second Attack", "Kirby 64: The Crystal Shards",
    "Killer Instinct Gold", "Cruisin USA", "Cruisin World", "Cruisin Exotica",
    "San Francisco Rush", "Rush 2: Extreme Racing", "F-1 World Grand Prix",
    "Beetle Adventure Racing", "Top Gear Rally", "Hydro Thunder", "Roadsters",
    "World Driver Championship", "NFL Blitz", "NFL Blitz 2000", "NBA Hangtime",
    "NBA Jam 99", "NBA Showtime: NBA on NBC", "NHL Breakaway 98", "NHL 99",
    "All-Star Baseball 2000", "All-Star Baseball 2001", "Triple Play 2000",
    "Tetrisphere", "Wetrix", "Quake", "Quake II", "Quake 64", "Hexen",
    "Doom 64", "Castlevania", "Castlevania: Legacy of Darkness",
    "ISS 64", "ISS Pro 98", "ISS 2000", "Worms Armageddon", "Mickey's Speedway USA",
    "Magical Tetris Challenge", "Tetris 64", "Glover", "Earthworm Jim 3D",
    "Rampage World Tour", "Mischief Makers", "Hybrid Heaven", "Penny Racers",
    "Chameleon Twist", "Chameleon Twist 2", "Carmageddon 64", "Dr. Mario 64",
    "Hey You, Pikachu", "Hot Wheels Turbo Racing", "Off Road Challenge",
    "Test Drive 64", "Vigilante 8", "Vigilante 8: Second Offense",
    "Twisted Edge Snowboarding", "South Park", "South Park Rally", "Quest 64",
    "Aidyn Chronicles", "Body Harvest", "Spider-Man",
    "Battletanx", "Battletanx: Global Assault", "Forsaken 64", "Daikatana",
    "Aero Fighters Assault", "Wipeout 64", "Extreme-G", "Extreme-G 2",
    "Indy Racing 2000", "Madden NFL 99", "Madden NFL 2000",
    "Pilotwings 64", "Blast Corps", "Sin and Punishment",
    "Ridge Racer 64", "Mace: The Dark Age", "California Speed",
    "Knife Edge: Nose Gunner", "Ogre Battle 64",
]


def _cart_id(title):
    """Deterministic 8-char hex cart ID, so the same title gives the same ID across calls."""
    return hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]


def _rng(seed):
    return random.Random(seed)


def detect():
    return {
        "cards": [{
            "path": "DEMO://card/",
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
