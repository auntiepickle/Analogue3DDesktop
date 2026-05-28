"""Bridge between the web UI and the analogue3d engine.

Every method here is exposed to JavaScript as ``window.pywebview.api.<name>()``.
Read-only methods (version, detect, list_backups) return plain data. Action
methods run an engine task, capture everything it prints, and return
``{ok, log, error}`` so the UI can show the output in its console pane.
"""

import io
import os
import base64
import zipfile
import contextlib
import threading

import analogue3d
from analogue3d import sdcard, controller, savestates, ui

# The GUI does its own confirmations; the engine must never block on a terminal
# prompt (there's no stdin behind a webview).
ui.ASSUME_YES = True

# stdout redirection is process-global, so only one action may run at a time.
_lock = threading.Lock()

# (path, mtime) -> base64 data URL, so we don't re-decode a 9 MB PNG every render.
_thumb_cache = {}


def _backup_dir():
    return os.path.join(os.path.dirname(sdcard.__file__), "backups")


def _run(task):
    """Run a no-arg callable, capturing stdout/stderr into a log string."""
    with _lock:
        buf = io.StringIO()
        ok, error = True, None
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                task()
            except Exception as e:  # an engine error must not kill the bridge
                ok, error = False, str(e)
                print(f"\nERROR: {e}")
        # Flash progress uses carriage returns; flatten them so the log reads cleanly.
        log = buf.getvalue().replace("\r", "\n")
        return {"ok": ok, "log": log, "error": error}


class Api:
    # ---------- read-only state ----------
    def version(self):
        return analogue3d.__version__

    def detect(self):
        cards = []
        try:
            for d in sdcard.get_potential_sd_cards():
                cards.append({
                    "path": d["path"],
                    "label": d["label"],
                    "free_gb": d["free_gb"],
                    "strong": d["score"] >= 4,
                    "reasons": d["reasons"],
                })
        except Exception:
            pass
        try:
            controllers = controller.connected_count()
        except Exception:
            controllers = 0
        return {"cards": cards, "controllers": controllers}

    def list_backups(self):
        out = []
        d = _backup_dir()
        if os.path.isdir(d):
            for name in sorted(os.listdir(d), reverse=True):
                if name.startswith("analogue3d_backup_") and name.endswith(".zip"):
                    p = os.path.join(d, name)
                    out.append({"name": name, "bytes": os.path.getsize(p)})
        return out

    # ---------- actions ----------
    def backup(self, root):
        return _run(lambda: sdcard.create_backup(root))

    def update_firmware(self, root):
        return _run(lambda: sdcard.install_firmware(root))

    def install_art(self, root, source=None):
        return _run(lambda: sdcard.install_labels(root, source or None))

    def update_controllers(self):
        def task():
            n = controller.connected_count()
            if n == 0:
                print("No 8BitDo 64 controller detected.")
                return
            print(f"Found {n} controller(s). Updating to the latest firmware...")

            def announce(cur, tgt):
                print(f"Flashing a controller {controller.format_version(cur)} "
                      f"-> {controller.format_version(tgt)} (do not unplug)...")

            s = controller.update_all(announce=announce)
            if s.get("note") and not s.get("updated"):
                print(s["note"])
            parts = [f"{s.get('updated', 0)} updated", f"{s.get('already', 0)} already current"]
            if s.get("failed"):
                parts.append(f"{s['failed']} failed")
            print("Done: " + ", ".join(parts) + ".")
        return _run(task)

    def restore(self, root, name):
        def task():
            path = os.path.join(_backup_dir(), os.path.basename(name))
            if not os.path.isfile(path):
                print("Backup not found: " + name)
                return
            print(f"Restoring {name} into {root} ...")
            with zipfile.ZipFile(path) as z:
                z.extractall(root)
            print("Restore complete.")
        return _run(task)

    def auto(self, root):
        def task():
            print("=== Auto: backup -> firmware -> art pack -> controllers ===")
            sdcard.create_backup(root)
            if not sdcard.install_firmware(root):
                print("Firmware step did not complete.")
            sdcard.install_labels(root)
            if controller.connected_count():
                controller.update_all(announce=lambda c, t: print(
                    f"Flashing a controller {controller.format_version(c)} "
                    f"-> {controller.format_version(t)}..."))
            print("\nAll done. Safely eject the card.")
        return _run(task)

    # ---------- save states (Memories) ----------
    def list_memories(self, root):
        try:
            games = savestates.find_game_states(root)
        except Exception:
            games = []
        out = []
        for g in games:
            out.append({
                "title": g["title"],
                "cart_id": g["cart_id"],
                "folder": g["folder"],
                "count": g["count"],
                "total_bytes": g["total_bytes"],
                "states": [{"name": s["name"], "when": s["when"], "bytes": s["bytes"]}
                           for s in g["states"]],
            })
        return {"available": bool(out), "limit": savestates.DEFAULT_KEEP, "games": out}

    def memory_thumbnail(self, root, folder, name):
        base = savestates.memories_dir(root)
        path = os.path.join(base, os.path.basename(folder), os.path.basename(name))
        if not os.path.isfile(path):
            return ""
        try:
            key = (path, os.path.getmtime(path))
        except OSError:
            return ""
        if key in _thumb_cache:
            return _thumb_cache[key]
        try:
            jpeg = savestates.thumbnail(path)
        except Exception:
            return ""
        url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
        _thumb_cache[key] = url
        return url

    def backup_memories(self, root):
        def task():
            games = savestates.find_game_states(root)
            if not games:
                print("No save states found on this card.")
                return
            total = 0
            for g in games:
                n = savestates.backup_game(g)
                total += n
                print(f"  {g['title']} [{g['cart_id']}]: backed up {n} state(s)")
            print(f"Done: archived {total} save state(s).")
        return _run(task)

    def trim_memory(self, root, folder, keep):
        def task():
            g = savestates.find_game(root, folder)
            if not g:
                print("Game not found on card: " + folder)
                return
            removed, kept = savestates.trim_to_latest(g, keep=max(0, int(keep)),
                                                      backup_first=True)
            print(f"{g['title']} [{g['cart_id']}]: archived and removed {removed} older "
                  f"state(s); kept the newest {kept} on the card.")
        return _run(task)

    def list_memory_backups(self):
        out = []
        for cart_id, paths in savestates.list_backups().items():
            for p in paths:
                out.append({
                    "cart_id": cart_id,
                    "name": os.path.basename(p),
                    "bytes": os.path.getsize(p) if os.path.isfile(p) else 0,
                })
        return out

    def restore_memory(self, root, cart_id, name):
        def task():
            backup_path = os.path.join(savestates._backup_dir(),
                                       os.path.basename(cart_id), os.path.basename(name))
            if not os.path.isfile(backup_path):
                print("Backup not found: " + name)
                return
            target = next((x for x in savestates.find_game_states(root)
                           if x["cart_id"] == cart_id), None)
            if not target:
                print("That game isn't on the card now, so there's nowhere to restore it.")
                return
            dest = savestates.restore_state(backup_path, target["path"])
            print(f"Restored {os.path.basename(name)} into {target['title']}.")
        return _run(task)
