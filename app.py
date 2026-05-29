#!/usr/bin/env python3
"""Analogue 3D Studio - a desktop GUI for the Analogue 3D Utility.

Launches a native window (pywebview) that loads web/index.html and bridges the
JavaScript UI to the analogue3d engine through the Api class. The heavy lifting
(firmware, art packs, backups, controller flashing) all lives in the shared
``analogue3d`` package; this app is just a face for it.
"""

import os
import sys
import json

_WIN_STATE = os.path.join(os.path.expanduser("~"), ".analogue3d", "studio_window.json")


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
        print("Analogue 3D Studio needs pywebview.\n"
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
                "auntiepickle.analogue3dstudio")
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

    studio = Api()
    window = webview.create_window("Analogue 3D Studio", index, js_api=studio, **win_kwargs)
    studio.attach_window(window)  # lets actions push live progress to the UI

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

    start_kwargs = {}
    if os.path.isfile(icon):
        start_kwargs["icon"] = icon
    webview.start(**start_kwargs)


if __name__ == "__main__":
    main()
