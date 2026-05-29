"""Bridge between the web UI and the analogue3d engine.

Every method here is exposed to JavaScript as ``window.pywebview.api.<name>()``.
Read-only methods (version, detect, list_backups) return plain data. Action
methods run an engine task, capture everything it prints, and return
``{ok, log, error}`` so the UI can show the output in its console pane.
"""

import io
import os
import re
import json
import base64
import zipfile
import contextlib
import threading

import analogue3d
from analogue3d import sdcard, controller, savestates, labels, saves, config, ui

STUDIO_VERSION = "0.1.0"

# The GUI does its own confirmations; the engine must never block on a terminal
# prompt (there's no stdin behind a webview).
ui.ASSUME_YES = True

# stdout redirection is process-global, so only one action may run at a time.
_lock = threading.Lock()

# (path, mtime) -> base64 data URL, so we don't re-decode a 9 MB PNG every render.
_thumb_cache = {}
_art_cache = {}

_FW_RE = re.compile(r"a3d_os_(\d+)_(\d+)_(\d+)\.bin$", re.IGNORECASE)


def _backup_dir():
    return config.backup_dir("backups")  # honor the configured backup location


def _labels_db(root):
    return os.path.join(root, "Library", "N64", "Images", "labels.db")


def _fw_version_from_name(name):
    m = _FW_RE.search(name or "")
    return tuple(int(g) for g in m.groups()) if m else None


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
    def __init__(self):
        self._window = None

    def attach_window(self, window):
        self._window = window

    def _emit(self, js):
        """Push a line of JS into the webview (used for live progress)."""
        w = self._window
        if w is not None:
            try:
                w.evaluate_js(js)
            except Exception:
                pass

    def _progress_cb(self):
        """A flash() progress callback that streams percent to the UI."""
        def cb(written, total, block, nblocks):
            pct = min(100, written * 100 // total) if total else 0
            self._emit(f"window.studioProgress&&studioProgress({pct},{block},{nblocks})")
        return cb

    def _steps_init(self, labels):
        self._emit("window.studioSteps&&studioSteps(" + json.dumps(labels) + ")")

    def _step(self, i, status):
        self._emit(f"window.studioStepStatus&&studioStepStatus({i},{json.dumps(status)})")

    def _step_note(self, i, note):
        self._emit(f"window.studioStepNote&&studioStepNote({i},{json.dumps(note)})")

    def _flash_announce(self, total, step_index=None):
        """An update_all/update_all_to announce callback that reports which
        controller (of how many) is being flashed, to the progress UI + log."""
        idx = [0]

        def announce(cur, tgt):
            idx[0] += 1
            self._emit(f"window.studioFlashTarget&&studioFlashTarget({idx[0]},{total})")
            if step_index is not None:
                self._step_note(step_index, f"updating #{idx[0]} of {total}")
            print(f"  controller {idx[0]} of {total}: "
                  f"{controller.format_version(cur)} -> {controller.format_version(tgt)}...")
        return announce

    # ---------- read-only state ----------
    def version(self):
        return STUDIO_VERSION

    # ---------- settings ----------
    def settings(self):
        return {"backup_root": config.get_backup_root(),
                "is_custom": config.is_custom_backup_root(),
                "default_root": config.default_backup_root(),
                "legacy_root": config.legacy_backup_root()}

    def set_backup_location(self):
        def task():
            w = self._window
            if w is None:
                print("No window for the folder picker.")
                return
            try:
                import webview
                picked = w.create_file_dialog(webview.FOLDER_DIALOG)
            except Exception as e:
                print("Could not open the folder picker: " + str(e))
                return
            if not picked:
                print("No folder chosen.")
                return
            path = picked[0] if isinstance(picked, (list, tuple)) else picked
            config.set_backup_root(path)
            print("Backup location set to:\n  " + path)
        return _run(task)

    def reset_backup_location(self):
        def task():
            config.set_backup_root("")
            print("Backup location reset to default:\n  " + config.get_backup_root())
        return _run(task)

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
    def backup(self, root, label=None):
        return _run(lambda: sdcard.create_backup(root, label))

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
            s = controller.update_all(progress=self._progress_cb(),
                                      announce=self._flash_announce(n))
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
            steps = ["Back up SD card (incl. save states)", "Update console firmware",
                     "Install cartridge art pack", "Update controllers"]
            self._steps_init(steps)
            print("=== Auto: backup -> firmware -> art pack -> controllers ===")

            self._step(0, "active")
            sdcard.create_backup(root)
            self._step(0, "done")

            self._step(1, "active")
            ok = sdcard.install_firmware(root)
            if not ok:
                print("Firmware step did not complete.")
            self._step(1, "done" if ok else "fail")

            self._step(2, "active")
            sdcard.install_labels(root)
            self._step(2, "done")

            n = controller.connected_count()
            if n:
                self._step(3, "active")
                self._step_note(3, f"{n} connected")
                controller.update_all(progress=self._progress_cb(),
                                      announce=self._flash_announce(n, step_index=3))
                self._step(3, "done")
                self._step_note(3, "")
            else:
                self._step(3, "skip")
                print("No controller connected - skipped.")
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
        return {"available": bool(out), "keep_default": savestates.DEFAULT_KEEP, "games": out}

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

    def archive_memories(self, root, label=None):
        def task():
            path, n = savestates.archive_all(root, label)
            if not path:
                print("No save states on this card to archive.")
                return
            size = os.path.getsize(path)
            print(f"Archived {n} save state(s) into {os.path.basename(path)} "
                  f"({size // (1024 * 1024)} MB).")
        return _run(task)

    def trim_memory(self, root, folder, keep):
        def task():
            g = savestates.find_game(root, folder)
            if not g:
                print("Game not found on card: " + folder)
                return
            snap, _ = savestates.archive_all(root)  # safety snapshot first
            if snap:
                print("Snapshot saved: " + os.path.basename(snap))
            removed, kept = savestates.trim_to_latest(g, keep=max(0, int(keep)))
            print(f"{g['title']} [{g['cart_id']}]: removed {removed} older state(s); "
                  f"kept the newest {kept} on the card.")
        return _run(task)

    def delete_memory(self, root, folder, name):
        def task():
            base = savestates.memories_dir(root)
            path = os.path.join(base, os.path.basename(folder), os.path.basename(name))
            if not os.path.isfile(path):
                print("Save state not found: " + name)
                return
            snap, _ = savestates.archive_all(root)  # safety snapshot first
            if snap:
                print("Snapshot saved: " + os.path.basename(snap))
            savestates.delete_state(path)
            print("Deleted from card: " + os.path.basename(name))
        return _run(task)

    def delete_memories(self, root, items):
        """Delete several selected save states at once (one safety snapshot first).
        items: list of {folder, name}."""
        def task():
            if not items:
                print("Nothing selected.")
                return
            snap, _ = savestates.archive_all(root)  # one snapshot covers them all
            if snap:
                print("Snapshot saved: " + os.path.basename(snap))
            base = savestates.memories_dir(root)
            n = 0
            for it in items:
                p = os.path.join(base, os.path.basename(it.get("folder", "")),
                                 os.path.basename(it.get("name", "")))
                if savestates.delete_state(p):
                    n += 1
            print(f"Deleted {n} selected save state(s) from the card.")
        return _run(task)

    # ---------- archive snapshots ----------
    def list_snapshots(self):
        out = []
        for s in savestates.list_snapshots():
            m = re.search(r"(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})(?:_(.+?))?\.zip$", s["name"])
            if m:
                when = f"{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}"
                if m.group(7):
                    when += "  ·  " + m.group(7)
            else:
                when = s["name"]
            out.append({
                "name": s["name"], "when": when, "bytes": s["bytes"],
                "count": sum(g["count"] for g in s["games"]), "games": s["games"],
            })
        return out

    def restore_memories(self, root, name):
        def task():
            try:
                n = savestates.restore_snapshot(root, name)
            except FileNotFoundError:
                print("Snapshot not found: " + name)
                return
            print(f"Restored all {n} save state(s) from {name} onto the card.")
        return _run(task)

    def restore_memories_game(self, root, name, cart_id):
        def task():
            try:
                n = savestates.restore_snapshot(root, name, cart_id=cart_id)
            except FileNotFoundError:
                print("Snapshot not found: " + name)
                return
            print(f"Restored {n} save state(s) for [{cart_id}] from {name}."
                  if n else "That game isn't in this snapshot.")
        return _run(task)

    def delete_snapshot(self, name):
        def task():
            if savestates.delete_snapshot(name):
                print("Deleted snapshot: " + os.path.basename(name))
            else:
                print("Snapshot not found: " + name)
        return _run(task)

    def clean_old_snapshots(self):
        def task():
            snaps = savestates.list_snapshots()  # newest first
            if len(snaps) <= 1:
                print("Nothing to clean - 1 or 0 snapshots.")
                return
            removed = 0
            for s in snaps[1:]:
                if savestates.delete_snapshot(s["name"]):
                    removed += 1
                    print("  deleted " + s["name"])
            print(f"Kept the newest snapshot, deleted {removed} older one(s).")
        return _run(task)

    # ---------- backup cleaning ----------
    def delete_backup(self, name):
        def task():
            p = os.path.join(_backup_dir(), os.path.basename(name))
            if not os.path.isfile(p):
                print("Backup not found: " + name)
                return
            os.remove(p)
            print("Deleted backup: " + os.path.basename(name))
        return _run(task)

    def clean_old_backups(self):
        def task():
            d = _backup_dir()
            zips = sorted([f for f in os.listdir(d)
                           if f.startswith("analogue3d_backup_") and f.endswith(".zip")],
                          reverse=True) if os.path.isdir(d) else []
            if len(zips) <= 1:
                print("Nothing to clean - 1 or 0 backups.")
                return
            removed = 0
            for name in zips[1:]:
                try:
                    os.remove(os.path.join(d, name))
                    removed += 1
                    print("  deleted " + name)
                except OSError:
                    pass
            print(f"Kept the newest backup, deleted {removed} older one(s).")
        return _run(task)

    # ---------- cartridge art ----------
    def cart_art_games(self, root):
        games = {}
        try:
            for g in savestates.find_game_states(root):
                games.setdefault(g["cart_id"], g["title"])
        except Exception:
            pass
        try:
            for s in saves.find_game_saves(root):
                games.setdefault(s["cart_id"], s["name"])
        except Exception:
            pass
        items = [{"cart_id": cid, "title": title}
                 for cid, title in sorted(games.items(), key=lambda kv: kv[1].lower())]
        return {"db_present": os.path.isfile(_labels_db(root)), "games": items}

    def cart_art(self, root, cart_id):
        db = _labels_db(root)
        if not os.path.isfile(db):
            return ""
        try:
            key = (db, os.path.getmtime(db), cart_id)
        except OSError:
            return ""
        if key in _art_cache:
            return _art_cache[key]
        try:
            img = labels.read_label_image(db, cart_id)
        except Exception:
            img = None
        if img is None:
            _art_cache[key] = ""
            return ""
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "PNG")
        url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        _art_cache[key] = url
        return url

    def set_cart_art(self, root, cart_id):
        def task():
            db = _labels_db(root)
            if not os.path.isfile(db):
                print("No labels.db on the card - install an art pack first.")
                return
            w = self._window
            if w is None:
                print("No window for the file picker.")
                return
            try:
                import webview
                picked = w.create_file_dialog(
                    webview.OPEN_DIALOG, allow_multiple=False,
                    file_types=("Images (*.png;*.jpg;*.jpeg;*.bmp;*.webp)", "All files (*.*)"))
            except Exception as e:
                print("Could not open the file picker: " + str(e))
                return
            if not picked:
                print("No image chosen.")
                return
            image_path = picked[0] if isinstance(picked, (list, tuple)) else picked
            try:
                result = labels.set_label(db, cart_id, image_path)
                labels.save_override(cart_id, image_path)  # survives art-pack re-installs
            except Exception as e:
                print("Failed: " + str(e))
                return
            verb = "Updated" if result == "updated" else "Added"
            print(f"{verb} art for cart {cart_id} from {os.path.basename(image_path)}. "
                  f"Saved as a custom override (kept across art-pack installs); "
                  f"resizes to 74x86 and shows on the console next boot.")
        return _run(task)

    # ---------- firmware versions ----------
    def versions(self, root):
        out = {"console_current": None, "console_latest": None,
               "console_update": False, "controllers": 0,
               "ctrl_current": None, "ctrl_latest": None, "ctrl_update": False}
        # console: what's staged on the card vs latest from analogue.co
        cur = None
        try:
            for e in os.listdir(root):
                v = _fw_version_from_name(e)
                if v:
                    cur = v
                    break
        except OSError:
            pass
        latest = None
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                _url, fname = sdcard.get_latest_firmware_url()
            latest = _fw_version_from_name(fname or "")
        except Exception:
            pass
        if cur:
            out["console_current"] = "%d.%d.%d" % cur
        if latest:
            out["console_latest"] = "%d.%d.%d" % latest
        if cur and latest:
            out["console_update"] = latest > cur
        # controller: read the connected pad vs latest from 8BitDo
        try:
            out["controllers"] = controller.connected_count()
        except Exception:
            pass
        if out["controllers"]:
            cur_int = None
            try:
                dev = controller.EightBitDo64().open()
                try:
                    cur_int = dev.read_version()
                finally:
                    dev.close()
                out["ctrl_current"] = controller.format_version(cur_int)
            except Exception:
                pass
            try:
                top = controller.fetch_firmware_list()[0]
                out["ctrl_latest"] = controller.format_version(top["version_int"])
                if cur_int is not None:
                    out["ctrl_update"] = top["version_int"] > cur_int
            except Exception:
                pass
        return out

    def controller_versions(self):
        try:
            vers = controller.fetch_firmware_list()
        except Exception as e:
            return {"ok": False, "versions": [], "error": str(e)}
        return {"ok": True, "versions": [
            {"version_int": e["version_int"], "label": controller.format_version(e["version_int"])}
            for e in vers]}

    def flash_controllers(self, version_int):
        def task():
            n = controller.connected_count()
            if n == 0:
                print("No 8BitDo 64 controller detected.")
                return
            vers = controller.fetch_firmware_list()
            meta = next((e for e in vers if e["version_int"] == int(version_int)), None)
            if meta is None:
                print("Firmware version not found: " + str(version_int))
                return
            tgt = controller.format_version(meta["version_int"])
            print(f"Flashing {n} controller(s) to {tgt} (do not unplug)...")
            s = controller.update_all_to(meta, progress=self._progress_cb(),
                                         announce=self._flash_announce(n))
            if s.get("note") and not s.get("updated"):
                print(s["note"])
            parts = [f"{s.get('updated', 0)} changed", f"{s.get('already', 0)} already on {tgt}"]
            if s.get("failed"):
                parts.append(f"{s['failed']} failed")
            print("Done: " + ", ".join(parts) + ".")
        return _run(task)
