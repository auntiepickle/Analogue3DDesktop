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
from analogue3d import sdcard, controller, savestates, labels, saves, ui

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
    return os.path.join(os.path.dirname(sdcard.__file__), "backups")


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

            s = controller.update_all(progress=self._progress_cb(), announce=announce)
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
            steps = ["Back up SD card", "Update console firmware",
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

            if controller.connected_count():
                self._step(3, "active")
                controller.update_all(progress=self._progress_cb(),
                    announce=lambda c, t: print(
                        f"Flashing a controller {controller.format_version(c)} "
                        f"-> {controller.format_version(t)}..."))
                self._step(3, "done")
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

        def _ts(item):  # the YYYYMMDDHHMMSS stamp in the filename
            m = re.search(r"(\d{14})", item["name"])
            return m.group(1) if m else ""
        out.sort(key=_ts, reverse=True)  # newest first
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

    def delete_memory(self, root, folder, name):
        def task():
            base = savestates.memories_dir(root)
            path = os.path.join(base, os.path.basename(folder), os.path.basename(name))
            if not os.path.isfile(path):
                print("Save state not found: " + name)
                return
            m = re.search(r"([0-9a-fA-F]{8})\s*$", folder)
            cart_id = m.group(1).lower() if m else "????????"
            savestates.backup_state(path, cart_id, os.path.basename(name))  # archive first
            os.remove(path)
            print(f"Archived and deleted: {os.path.basename(name)}")
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

    def delete_memory_backup(self, cart_id, name):
        def task():
            p = os.path.join(savestates._backup_dir(),
                             os.path.basename(cart_id), os.path.basename(name))
            if not os.path.isfile(p):
                print("Archived state not found: " + name)
                return
            os.remove(p)
            print("Deleted archived state: " + os.path.basename(name))
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
            except Exception as e:
                print("Failed: " + str(e))
                return
            verb = "Updated" if result == "updated" else "Added"
            print(f"{verb} art for cart {cart_id} from {os.path.basename(image_path)}. "
                  f"It resizes to 74x86 and shows on the console next boot.")
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

            def announce(cur, target):
                print(f"  a controller {controller.format_version(cur)} -> "
                      f"{controller.format_version(target)}...")

            s = controller.update_all_to(meta, progress=self._progress_cb(), announce=announce)
            if s.get("note") and not s.get("updated"):
                print(s["note"])
            parts = [f"{s.get('updated', 0)} changed", f"{s.get('already', 0)} already on {tgt}"]
            if s.get("failed"):
                parts.append(f"{s['failed']} failed")
            print("Done: " + ", ".join(parts) + ".")
        return _run(task)
