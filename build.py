#!/usr/bin/env python3
"""Build a standalone Analogue 3D Desktop binary with PyInstaller.

    pip install pyinstaller
    python build.py

Produces a single windowed executable in dist/:
    Windows : dist/Analogue3DDesktop.exe   (Edge WebView2 backend, via pythonnet)
    macOS   : dist/Analogue3DDesktop.app   (Cocoa/WebKit backend)
    Linux   : dist/Analogue3DDesktop       (GTK/WebKit backend)

The engine (analogue3d), the web UI, the icon (Windows), and the pywebview
backend are bundled. On Windows the target just needs the Edge WebView2 Runtime
(ships with Win11 and current Win10).
"""

import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SEP = ";" if sys.platform == "win32" else ":"

# If the engine is checked out as a sibling repo (local-dev / editable case),
# point PyInstaller at its source so it can bundle the `analogue3d` package - an
# editable install is an import hook, not files PyInstaller can follow. (A normal
# `pip install analogue3d`, e.g. in CI, needs no --paths.)
paths = []
_core = os.path.normpath(os.path.join(HERE, "..", "Analogue3DUtility"))
if os.path.isdir(os.path.join(_core, "analogue3d")):
    paths += ["--paths", _core]

# Windows talks to Edge WebView2 through pythonnet (clr); bundle it + the icon.
# macOS/Linux use native backends (pyobjc / PyGObject) that pywebview pulls in.
platform_args = []
if sys.platform == "win32":
    platform_args += [
        "--icon", os.path.join("assets", "icon.ico"),
        "--collect-all", "clr_loader",
        "--collect-all", "pythonnet",
        "--hidden-import", "clr",
    ]

args = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--name", "Analogue3DDesktop",
    "--onefile", "--windowed",
    "--add-data", f"web{SEP}web",
    "--add-data", f"assets{SEP}assets",
    *paths,
    "--collect-submodules", "analogue3d",
    "--collect-all", "webview",
    "--hidden-import", "hid",
    "--hidden-import", "requests",  # used directly by the in-app updater download
    *platform_args,
    "app.py",
]

print("Running PyInstaller...\n  " + " ".join(args))
subprocess.check_call(args, cwd=HERE)

name = "Analogue3DDesktop"
if sys.platform == "win32":
    out = os.path.join(HERE, "dist", name + ".exe")
elif sys.platform == "darwin":
    out = os.path.join(HERE, "dist", name + ".app")
else:
    out = os.path.join(HERE, "dist", name)
print("\nBuilt:", out)
