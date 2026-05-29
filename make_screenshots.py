#!/usr/bin/env python3
"""Regenerate the README screenshots from the live GUI.

Launches the real app, lets it auto-detect the SD card, then scrolls to each
section and grabs the window's client area (no OS chrome). DPI-aware so the
client rect and screen coordinates line up on scaled displays.

    python make_screenshots.py
"""

import os
import time
import ctypes
import ctypes.wintypes as wt
import threading

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
INDEX = os.path.join(HERE, "web", "index.html")
SHOTS = os.path.join(HERE, "assets", "screenshots")
TITLE = "Analogue 3D Desktop"

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
    time.sleep(6)  # load + SD detect + art/saves populate
    grab(window, "main.png", "window.scrollTo(0,0)")
    grab(window, "cartart.png", SCROLL_TO + "('Cartridge')", settle=2.2)
    # expand the first save-state game so the thumbnails show
    window.evaluate_js("var h=document.querySelector('.game-head'); if(h) h.click();")
    time.sleep(2.5)
    grab(window, "savestates.png", SCROLL_TO + "('Save states')", settle=1.6)
    window.destroy()


if __name__ == "__main__":
    api = Api()
    window = webview.create_window(TITLE, INDEX, js_api=api, on_top=True,
                                   width=1000, height=820, background_color="#0d0d0f")
    api.attach_window(window)
    threading.Thread(target=worker, args=(window,), daemon=True).start()
    webview.start()
    print("done")
