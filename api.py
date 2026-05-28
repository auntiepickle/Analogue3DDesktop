"""Bridge between the web UI and the analogue3d engine.

Every method here is exposed to JavaScript as ``window.pywebview.api.<name>()``.
Read-only methods (version, detect, list_backups) return plain data. Action
methods run an engine task, capture everything it prints, and return
``{ok, log, error}`` so the UI can show the output in its console pane.
"""

import io
import os
import zipfile
import contextlib
import threading

import analogue3d
from analogue3d import sdcard, controller, ui

# The GUI does its own confirmations; the engine must never block on a terminal
# prompt (there's no stdin behind a webview).
ui.ASSUME_YES = True

# stdout redirection is process-global, so only one action may run at a time.
_lock = threading.Lock()


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
