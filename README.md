# Analogue 3D Studio

A desktop GUI for the [Analogue 3D Utility](https://github.com/auntiepickle/Analogue3DUtility) —
the same engine (firmware updates, cartridge art packs, save backups, and 8BitDo 64
controller flashing), with a point-and-click black-and-gold interface for people who'd
rather not use a terminal.

This repo is intentionally thin: it's a [pywebview](https://pywebview.flowrl.com/) window
that loads a small web UI (`web/`) and bridges it to the shared `analogue3d` Python
package, which does all the real work.

## Run it

```sh
pip install pywebview
pip install -e ../Analogue3DUtility   # the engine (local dev)
python app.py
```

On Windows it uses the built-in Edge WebView2 runtime — nothing else to install.

## How it's wired

- `app.py` — launches the native window.
- `api.py` — the `Api` class exposed to JavaScript (`window.pywebview.api.*`). Read-only
  methods return data; action methods run an engine task and return its captured log.
- `web/` — `index.html`, `style.css`, `app.js`: the interface.

The CLI (`python a3d.py` in the core repo) and this GUI are two faces on the same engine.

## Status

Early. Verified to import and launch; visuals and the save-state ("Memories") manager are
in progress.
