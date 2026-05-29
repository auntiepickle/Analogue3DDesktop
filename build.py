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
import re
import plistlib
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SEP = ";" if sys.platform == "win32" else ":"
BUNDLE_ID = "co.auntiepickle.analogue3ddesktop"


def _app_version():
    """Read APP_VERSION from api.py by regex, without importing it (so the build
    doesn't need the GUI runtime deps just to read a string)."""
    try:
        with open(os.path.join(HERE, "api.py"), encoding="utf-8") as f:
            m = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', f.read())
        return m.group(1) if m else "0"
    except OSError:
        return "0"


def _patch_info_plist(app_path):
    """Give the macOS .app proper bundle metadata (identifier, version, display
    name, Retina). PyInstaller writes a bare Info.plist; we fill in the rest."""
    plist = os.path.join(app_path, "Contents", "Info.plist")
    with open(plist, "rb") as f:
        info = plistlib.load(f)
    ver = _app_version()
    info.update({
        "CFBundleName": "Analogue 3D Desktop",
        "CFBundleDisplayName": "Analogue 3D Desktop",
        "CFBundleShortVersionString": ver,
        "CFBundleVersion": ver,
        "CFBundleIdentifier": BUNDLE_ID,
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.utilities",
    })
    with open(plist, "wb") as f:
        plistlib.dump(info, f)
    print(f"patched Info.plist (version {ver})")

# If the engine is checked out as a sibling repo (local-dev / editable case),
# point PyInstaller at its source so it can bundle the `analogue3d` package - an
# editable install is an import hook, not files PyInstaller can follow. (A normal
# `pip install analogue3d`, e.g. in CI, needs no --paths.)
paths = []
_core = os.path.normpath(os.path.join(HERE, "..", "Analogue3DUtility"))
if os.path.isdir(os.path.join(_core, "analogue3d")):
    paths += ["--paths", _core]

# Packaging mode: a single self-contained exe on Windows/Linux; a proper onedir
# .app on macOS - it launches faster (no per-run self-extraction) and is the
# layout Apple notarization expects.
if sys.platform == "darwin":
    mode_args = ["--onedir", "--windowed"]
else:
    mode_args = ["--onefile", "--windowed"]

# Windows talks to Edge WebView2 through pythonnet (clr); bundle it + the .ico.
# macOS gets the .icns + a bundle identifier. Linux uses the native GTK/WebKit
# backend pywebview pulls in (and isn't shipped as a binary - run from source).
platform_args = []
if sys.platform == "win32":
    platform_args += [
        "--icon", os.path.join("assets", "icon.ico"),
        "--collect-all", "clr_loader",
        "--collect-all", "pythonnet",
        "--hidden-import", "clr",
    ]
elif sys.platform == "darwin":
    platform_args += [
        "--icon", os.path.join("assets", "icon.icns"),
        "--osx-bundle-identifier", BUNDLE_ID,
    ]

args = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--name", "Analogue3DDesktop",
    *mode_args,
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
    _patch_info_plist(out)
else:
    out = os.path.join(HERE, "dist", name)
print("\nBuilt:", out)
