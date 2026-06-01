#!/usr/bin/env python3
"""Analogue 3D Desktop - a desktop GUI for the Analogue 3D Utility.

Launches a native window (pywebview) that loads web/index.html and bridges the
JavaScript UI to the analogue3d engine through the Api class. The heavy lifting
(firmware, art packs, backups, controller flashing) all lives in the shared
``analogue3d`` package; this app is just a face for it.
"""

import os
import sys
import json

_WIN_STATE = os.path.join(os.path.expanduser("~"), ".analogue3d", "desktop_window.json")


def _load_window_state():
    try:
        with open(_WIN_STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_window_state(state):
    try:
        os.makedirs(os.path.dirname(_WIN_STATE), exist_ok=True)
        with open(_WIN_STATE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except OSError:
        pass


def main():
    try:
        import webview
    except ImportError:
        print("Analogue 3D Desktop needs pywebview.\n"
              "  pip install pywebview\n"
              "(On Windows it uses the built-in Edge WebView2 runtime.)")
        sys.exit(1)

    try:
        from api import Api
    except ImportError as e:
        print("Couldn't load the engine. Install the core package:\n"
              "  pip install analogue3d\n"
              "  (or, for local dev: pip install -e ../Analogue3DUtility)\n"
              f"Details: {e}")
        sys.exit(1)

    here = os.path.dirname(os.path.abspath(__file__))
    index = os.path.join(here, "web", "index.html")
    icon = os.path.join(here, "assets", "icon.ico")

    # Screenshot-capture aid: A3D_THEME=jungle / A3D_MODE=tinker launches with
    # those picks via URL hash, no localStorage manipulation. Read by
    # getTheme() / getMode() in app.js.
    _hash_parts = []
    if os.environ.get("A3D_THEME"): _hash_parts.append("theme=" + os.environ["A3D_THEME"])
    if os.environ.get("A3D_MODE"):  _hash_parts.append("mode=" + os.environ["A3D_MODE"])
    if _hash_parts:
        index = "file:///" + index.replace(os.sep, "/") + "#" + "&".join(_hash_parts)

    if sys.platform == "win32":
        try:
            import ctypes
            # Per-monitor DPI awareness so the webview renders crisply (not
            # bitmap-stretched/blurry) on displays scaled above 100%.
            try:
                ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
            except Exception:
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
                except Exception:
                    ctypes.windll.user32.SetProcessDPIAware()
            # Give the process its own taskbar identity so Windows shows our icon,
            # not the generic Python one.
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "auntiepickle.analogue3ddesktop")
        except Exception:
            pass

    # Remember whether the window was maximized last time. (Exact size/position
    # persistence is unreliable through pywebview's resize events on scaled
    # displays, so we keep just the maximized state, which is solid.)
    st = _load_window_state()
    win_kwargs = dict(width=1000, height=760, min_size=(860, 640),
                      background_color="#0d0d0f")
    if st.get("maximized"):
        win_kwargs["maximized"] = True

    api_obj = Api()
    window = webview.create_window("Analogue 3D Desktop", index, js_api=api_obj, **win_kwargs)
    api_obj.attach_window(window)  # lets actions push live progress to the UI

    maxed = {"on": bool(st.get("maximized"))}

    def on_max(*a):
        maxed["on"] = True

    def on_restore(*a):
        maxed["on"] = False

    def on_closing(*a):
        _save_window_state({"maximized": maxed["on"]})

    for name, fn in (("maximized", on_max), ("restored", on_restore),
                     ("closing", on_closing)):
        try:
            getattr(window.events, name).__iadd__(fn)
        except Exception:
            pass

    # Persist the WebView2 profile (cookies + localStorage) so the user's
    # picked theme/mode survives a restart. pywebview defaults to
    # private_mode=True, which wipes a3d:theme / a3d:mode / a3d:clear on every
    # exit — that's why the theme picker felt amnesiac.
    storage = os.path.join(os.path.expanduser("~"), ".analogue3d", "webview")
    # Drop the HTTP/JS code cache on every launch so an updated build's new
    # HTML/CSS/JS isn't shadowed by the prior version's cached bytes. Local
    # Storage (where theme/mode prefs live) sits in a sibling dir and is
    # preserved.
    import shutil
    _cache_root = os.path.join(storage, "EBWebView", "Default")
    for _sub in ("Cache", "Code Cache", "GPUCache"):
        shutil.rmtree(os.path.join(_cache_root, _sub), ignore_errors=True)
    start_kwargs = {"private_mode": False, "storage_path": storage}
    if os.path.isfile(icon):
        start_kwargs["icon"] = icon
    webview.start(**start_kwargs)


if __name__ == "__main__":
    main()
