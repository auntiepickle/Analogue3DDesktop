<p align="center">
  <img src="assets/banner.svg?v=0.2.0" alt="Analogue 3D Desktop" width="100%">
</p>

# Analogue 3D Desktop

A desktop GUI for the Analogue 3D — a point-and-click, black-and-gold interface
for updating the console, flashing the 8BitDo 64 controller, managing save
states, installing cartridge art, and backing it all up. It's the friendly face
on the same engine as the [Analogue 3D Utility](https://github.com/auntiepickle/Analogue3DUtility)
CLI: the shared `analogue3d` Python package does the real work, and this app is a
[pywebview](https://pywebview.flowrl.com/) window over it.

## Features

- **Updates** — see the console firmware on the card and the controller firmware
  vs. the latest available, with an "up to date / update available" badge. Update
  console firmware, and flash one or *all* connected controllers to any official
  version (downgrades included) with a live, determinate progress bar.
- **Backups** — zip up Library, Settings, and Memories (save states); restore a
  backup; delete one or keep only the latest.
- **Save states (Memories)** — a per-game, paginated, filterable browser with
  screenshot thumbnails. Take a **snapshot** of every save state and restore the
  whole thing or just one game; trim a game to its newest N; delete individual
  states. Destructive actions take a safety snapshot first.
- **Cartridge art** — a paginated gallery of your games' box art. Install the
  [RetroGameCorps](https://github.com/retrogamecorps/Analogue-3D-Images) art pack
  or a custom URL, or set a **custom image per cartridge**.
- **Auto** — one click runs the lot (back up incl. save states, console firmware,
  art pack, every controller) with a live step checklist.
- **Settings** — a configurable backup location (defaults to
  `~/Documents/Analogue3D`), shared with the CLI.
- Live device detection (plug/unplug), styled in-app dialogs, and an app icon.

## Screenshots

**Tinker mode** — the full instrument panel. A persistent rail with SD card,
controller, and a one-click **AUTO** action; the **UPDATES** block (console
firmware + per-controller flash with a determinate progress bar); **BACKUPS**
(zip Library/Settings/Memories, restore, clean); and the **CARTRIDGE ART**
gallery with your games' box art — paginate, filter, install a pack, or set a
custom image per cartridge.

<p align="center">
  <img src="assets/screenshots/main.png?v=0.5.0" alt="Tinker mode: persistent rail with SD card + controller status and the AUTO action, plus the main grid showing UPDATES (console firmware + controller flash) and BACKUPS (back up + restore/clean), with the CARTRIDGE ART gallery of real game boxes below" width="92%">
</p>

**Minimal mode** — the friendly face. SD card · console · controller status
across the top, one big **DO EVERYTHING** button below. Same engine, same
themes, no extra surface area to read.

<p align="center">
  <img src="assets/screenshots/minimal.png?v=0.5.0" alt="Minimal mode: SD card connected, console up to date, controller status with version arrow, and a single big DO EVERYTHING action" width="92%">
</p>

## Colorways

Ten accent themes mirror Analogue 3D, Analogue Pocket, and N64 Funtastic editions. Switch in Settings.

<p align="center">
  <img src="assets/colorways.svg?v=0.3.0" alt="Color swatch — the 10 themes: Gold, White, Glow, Ice, Jungle, Watermelon, Grape, Fire, Atomic, Smoke" width="90%">
</p>

## Download

Grab the build for your OS from the
[Releases page](https://github.com/auntiepickle/Analogue3DDesktop/releases) — no Python needed:

- **Windows** — `Analogue3DDesktop-windows.exe`. Uses the built-in **Edge WebView2 runtime**
  (ships with Windows 11 and current Windows 10).
- **macOS** — download `Analogue3DDesktop-macos.dmg`, open it, and drag **Analogue 3D Desktop**
  into your **Applications** folder. The app is ad-hoc signed (so it won't be flagged as
  "damaged") but not yet notarized, so the **first** launch needs a one-time
  **right-click → Open** — after that, just double-click. To skip the Gatekeeper prompt
  entirely, download with `curl` instead of a browser (curl downloads aren't quarantined):
  ```sh
  curl -L -o ~/Downloads/Analogue3DDesktop.dmg \
    https://github.com/auntiepickle/Analogue3DDesktop/releases/latest/download/Analogue3DDesktop-macos.dmg
  ```
  (Once installed, the app updates itself from within — it pulls
  `Analogue3DDesktop-macos.zip` automatically.)
- **Linux** — **run from source** (below). pywebview's GTK/WebKit backend doesn't bundle into
  a portable binary reliably, so there's no Linux download.

## Run from source

```sh
pip install pywebview
pip install analogue3d        # the engine (or: pip install -e ../Analogue3DUtility)
python app.py
```

On Windows it uses the built-in Edge WebView2 runtime — nothing else to install.

## Build a standalone binary

```sh
pip install pyinstaller
python build.py
```

This produces `Analogue3DDesktop.exe` on Windows and a proper `Analogue3DDesktop.app`
on macOS (built `--onedir` with the icon and bundle metadata). It bundles the engine,
the web UI, the icon, and the pywebview backend, so it runs with nothing else installed —
on Windows the target machine just needs the Microsoft Edge WebView2 Runtime (ships with
Windows 11 and current Windows 10). The `.dmg`/`.zip` packaging and macOS signing happen
in CI (see `.github/workflows/release.yml`).

## How it's wired

- `app.py` — launches the native window and sets the taskbar identity + icon.
- `api.py` — the `Api` class exposed to JavaScript (`window.pywebview.api.*`).
  Read-only methods return data; action methods run an engine task, stream
  progress, and return its captured log.
- `web/` — `index.html`, `style.css`, `app.js`: the interface.
- `build.py` — the PyInstaller build.

The CLI (`python a3d.py` in the core repo) and this GUI are two faces on the same
`analogue3d` engine.

## Design language

The Desktop app is built around an **instrument-panel** metaphor — hi-fi hardware, not a dashboard. Mono uppercase labels paired with sans values, hairline 1px borders, one accent at a time, imperative copy. Theming follows the actual Analogue 3D, Analogue Pocket, and N64 Funtastic editions.

- **[docs/BRANDING.md](docs/BRANDING.md)** — six brand pillars, voice rules, the wordmark, logo concept.
- **[docs/THEMING.md](docs/THEMING.md)** — how the 10 themes work, rules when adding an 11th, the Funtastic translucent overlay.
- **[docs/REDESIGN.md](docs/REDESIGN.md)** — what the dual-mode UI redesign changed and why.
- **[docs/CLI-UPDATES.md](docs/CLI-UPDATES.md)** — reviewer-driven recommendations for landing the same language in the CLI (separate PR).
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — testing notes (incl. demo + theme env vars), code style, voice.
