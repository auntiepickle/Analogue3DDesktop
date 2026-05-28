#!/usr/bin/env python3
"""Analogue 3D Studio - a desktop GUI for the Analogue 3D Utility.

Launches a native window (pywebview) that loads web/index.html and bridges the
JavaScript UI to the analogue3d engine through the Api class. The heavy lifting
(firmware, art packs, backups, controller flashing) all lives in the shared
``analogue3d`` package; this app is just a face for it.
"""

import os
import sys


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
        # Give the process its own taskbar identity so Windows shows our icon,
        # not the generic Python one.
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "auntiepickle.analogue3dstudio")
        except Exception:
            pass

    studio = Api()
    window = webview.create_window(
        "Analogue 3D Studio",
        index,
        js_api=studio,
        width=1000, height=760, min_size=(860, 640),
        background_color="#0d0d0f",
    )
    studio.attach_window(window)  # lets actions push live progress to the UI

    start_kwargs = {}
    if os.path.isfile(icon):
        start_kwargs["icon"] = icon
    webview.start(**start_kwargs)


if __name__ == "__main__":
    main()
