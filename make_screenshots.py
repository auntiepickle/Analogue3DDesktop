#!/usr/bin/env python3
"""Regenerate the README hero screenshot from the live demo GUI.

Launches the real app in demo mode, maximizes the window, waits for the
gallery art to load, and grabs the client area (no OS chrome). DPI-aware so
the client rect and screen coordinates line up on scaled displays.

    python make_screenshots.py
"""

import os
import time
import ctypes
import ctypes.wintypes as wt
import threading

# Demo + theme + mode — set BEFORE the engine imports read env
os.environ.setdefault("A3D_DEMO", "1")
os.environ.setdefault("A3D_THEME", "gold")
os.environ.setdefault("A3D_MODE", "tinker")

# DPI-aware BEFORE webview loads, so GetClientRect + screen coords are physical px
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()

import webview
from PIL import ImageGrab
from api import Api

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "assets", "screenshots")
TITLE = "Analogue 3D Desktop"

# Same theme/mode → URL-hash bridge that app.py uses so getTheme()/getMode()
# in web/app.js pick up our env overrides.
_idx = os.path.join(HERE, "web", "index.html")
_parts = []
if os.environ.get("A3D_THEME"): _parts.append("theme=" + os.environ["A3D_THEME"])
if os.environ.get("A3D_MODE"):  _parts.append("mode=" + os.environ["A3D_MODE"])
INDEX = ("file:///" + _idx.replace(os.sep, "/") + "#" + "&".join(_parts)) if _parts else _idx

user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [("left", wt.LONG), ("top", wt.LONG),
                ("right", wt.LONG), ("bottom", wt.LONG)]


class POINT(ctypes.Structure):
    _fields_ = [("x", wt.LONG), ("y", wt.LONG)]


def client_bbox():
    hwnd = user32.FindWindowW(None, TITLE)
    if not hwnd:
        return None
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    r = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    tl = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(tl))
    return (tl.x, tl.y, tl.x + r.right, tl.y + r.bottom)


def grab(window, name, js, settle=1.4):
    window.evaluate_js(js)
    time.sleep(settle)
    bbox = client_bbox()
    if not bbox:
        print("!! window not found for", name)
        return
    img = ImageGrab.grab(bbox=bbox, all_screens=True)
    img.save(os.path.join(SHOTS, name))
    print("saved", name, img.size)


SCROLL_TO = ("(function(t){var s=[].slice.call(document.querySelectorAll('section'))"
             ".filter(function(x){var h=x.querySelector('h2');return h&&h.textContent"
             ".indexOf(t)>=0})[0];if(s)s.scrollIntoView({block:'start'});})")


def worker(window):
    time.sleep(7)  # demo init + art + galleries populate
    # Tinker (advanced) mode — the full instrument-panel grid
    window.evaluate_js("if(window.setMode) setMode('tinker');")
    grab(window, "main.png", "window.scrollTo(0,0)", settle=1.8)
    # Save states / Memories — scroll there and expand the first game so the
    # screenshot thumbnails show. This is the genuinely novel surface.
    grab(window, "savestates.png", SCROLL_TO + "('Save states')", settle=1.6)
    window.evaluate_js("var h=document.querySelector('.game-head'); if(h) h.click();")
    time.sleep(2.0)
    grab(window, "savestates.png", SCROLL_TO + "('Save states')", settle=1.4)
    # Minimal mode — the friendly "Do everything" face
    window.evaluate_js("if(window.setMode) setMode('minimal');")
    grab(window, "minimal.png", "window.scrollTo(0,0)", settle=1.8)
    window.destroy()


if __name__ == "__main__":
    api = Api()
    # maximized=True puts the window at the user's actual screen size — the
    # layout the user sees day-to-day, which is what the README should show.
    window = webview.create_window(TITLE, INDEX, js_api=api,
                                   width=1000, height=820, maximized=True,
                                   background_color="#0d0d0f")
    api.attach_window(window)
    threading.Thread(target=worker, args=(window,), daemon=True).start()
    # private_mode=True so the script's setMode('tinker')/setMode('minimal')
    # writes don't pollute the developer's real ~/.analogue3d/webview Local
    # Storage (app.py runs persistent, so the same profile would be shared).
    webview.start(private_mode=True)
    print("done")
