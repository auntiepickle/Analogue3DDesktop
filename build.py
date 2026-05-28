#!/usr/bin/env python3
"""Build a standalone Analogue 3D Studio binary with PyInstaller.

    pip install pyinstaller
    python build.py

Produces a single windowed executable in dist/:
    Windows : dist/Analogue3DStudio.exe   (uses the built-in Edge WebView2 runtime)
    macOS   : dist/Analogue3DStudio.app
    Linux   : dist/Analogue3DStudio

The engine (analogue3d), the web UI, the icon, and the pywebview backend are all
bundled, so the binary runs with nothing else installed (on Windows the target
machine just needs the Microsoft Edge WebView2 Runtime, which ships with Win11
and current Win10).
"""

import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SEP = ";" if sys.platform == "win32" else ":"
ICON = os.path.join("assets", "icon.ico" if sys.platform == "win32" else "icon.png")

# If the engine is checked out as a sibling repo (the local-dev / editable case),
# point PyInstaller at its source so it can actually bundle the `analogue3d`
# package - an editable (pip install -e) install is an import hook, not files
# PyInstaller can follow. (A normal `pip install analogue3d` needs no --paths.)
_extra = []
_core = os.path.normpath(os.path.join(HERE, "..", "Analogue3DUtility"))
if os.path.isdir(os.path.join(_core, "analogue3d")):
    _extra += ["--paths", _core]

args = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--name", "Analogue3DStudio",
    "--onefile", "--windowed",
    "--icon", ICON,
    "--add-data", f"web{SEP}web",
    "--add-data", f"assets{SEP}assets",
    *_extra,
    "--collect-submodules", "analogue3d",
    "--collect-all", "webview",
    "--collect-all", "clr_loader",
    "--collect-all", "pythonnet",
    "--hidden-import", "clr",
    "--hidden-import", "hid",
    "app.py",
]

print("Running PyInstaller...\n  " + " ".join(args))
subprocess.check_call(args, cwd=HERE)

out = os.path.join(HERE, "dist", "Analogue3DStudio" + (".exe" if sys.platform == "win32" else ""))
print("\nBuilt:", out)
