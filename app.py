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

# Windows .NET runtime: force .NET Framework (netfx) before any pywebview import.
# pywebview's WinForms backend opens with:
#       try:
#           import clr
#       except Exception:
#           os.environ['PYTHONNET_RUNTIME'] = 'coreclr'   # <- silent downgrade
#           import clr
# so if the first `import clr` throws, pywebview forces CoreCLR (.NET 5+), which
# then resolves a .NET 9 WinForms whose parent 'System.Private.CoreLib,
# Version=9.0.0.0' can't be bound — the "Could not load type 'System.Object'"
# crash at winforms.py load time.
#
# IMPORTANT: `pythonnet.load("netfx")` is NOT sufficient. pythonnet.load() ignores
# its runtime argument if a runtime was already *selected* — it silently runs on
# whatever was chosen (e.g. CoreCLR), with no exception. So we must (1) force the
# netfx runtime explicitly with set_runtime() — which overrides a prior selection —
# and (2) VERIFY the live runtime really is .NET Framework, failing LOUD if not.
# That makes "silently running on CoreCLR" impossible. A breadcrumb is written to
# ~/.analogue3d/netfx-startup.log so a failing run is self-diagnosing even if the
# dialog path is somehow bypassed.
if sys.platform == "win32":
    os.environ["PYTHONNET_RUNTIME"] = "netfx"      # hard set, not setdefault
    _netfx_err = None
    _runtime_kind = None
    try:
        import pythonnet
        from clr_loader import get_netfx
        try:
            # Force the netfx runtime, overriding anything already selected.
            # Raises "already been loaded" if a runtime is *loaded* (can't switch);
            # raises something else if .NET Framework / the netfx shim is missing.
            pythonnet.set_runtime(get_netfx())
        except RuntimeError as _se:
            if "already" not in str(_se).lower():
                raise                              # netfx genuinely unavailable -> fail loud
        pythonnet.load()
        import clr  # noqa: F401  (no-op now; confirms the runtime is live)
        _ri = pythonnet.get_runtime_info()
        _runtime_kind = _ri.kind if _ri else None
        if not _runtime_kind or "Framework" not in _runtime_kind:
            raise RuntimeError("active .NET runtime is %r, not .NET Framework" % (_runtime_kind,))
    except Exception as _e:
        _netfx_err = _e
    # Pre-resolve WinForms + diagnose. Even under netfx, pywebview later does
    # Assembly.LoadWithPartialName('System.Windows.Forms') + GetType('...OpenFileDialog');
    # on some Win10 boxes with an incomplete .NET Framework GAC, fusion falls through to a
    # .NET 9 WinForms whose parent 'System.Private.CoreLib 9.0.0.0' can't bind -> crash.
    # Force-load the FRAMEWORK WinForms by strong name so pywebview reuses that one, and
    # record what actually resolves so a failing run is diagnosable from the log.
    _wf_info = "skipped"
    if _netfx_err is None:
        _wf_parts = []
        try:
            clr.AddReference("System.Windows.Forms, Version=4.0.0.0, Culture=neutral, "
                             "PublicKeyToken=b77a5c561934e089")
            _wf_parts.append("strongref=OK")
        except Exception as _e1:
            _wf_parts.append("strongref=ERR:%r" % (_e1,))
        try:
            from System.Reflection import Assembly as _Asm
            _wf = _Asm.LoadWithPartialName("System.Windows.Forms")
            _wf_parts.append("resolved=%s" % (_wf.FullName if _wf else "None",))
            _wf_parts.append("loc=%s" % (_wf.Location if _wf else "?",))
            try:
                _ofd = _wf.GetType("System.Windows.Forms.OpenFileDialog")
                _wf_parts.append("OpenFileDialog=%s" % ("OK" if _ofd else "None",))
            except Exception as _e3:
                _wf_parts.append("GetType=ERR:%r" % (_e3,))
        except Exception as _e2:
            _wf_parts.append("LoadWithPartialName=ERR:%r" % (_e2,))
        _wf_info = " | ".join(_wf_parts)
    try:
        _logdir = os.path.join(os.path.expanduser("~"), ".analogue3d")
        os.makedirs(_logdir, exist_ok=True)
        with open(os.path.join(_logdir, "netfx-startup.log"), "w", encoding="utf-8") as _lf:
            _lf.write("runtime=%r\nerror=%s\nwinforms=%s\n" % (_runtime_kind,
                      repr(_netfx_err) if _netfx_err is not None else "none", _wf_info))
    except Exception:
        pass
    if _netfx_err is not None:
        _msg = (
            "Analogue 3D Desktop couldn't start on the Windows .NET Framework runtime.\n\n"
            "It ended up on: %s\n\n"
            "This app needs Microsoft .NET Framework 4.7.2 or newer, which is normally\n"
            "built into Windows 10 and 11. If this keeps happening:\n"
            "  • Run Windows Update (it installs .NET Framework), then retry.\n"
            "  • Reinstall Analogue 3D Desktop.\n"
            "  • On a Windows-on-ARM (ARM64) PC this build isn't supported yet.\n\n"
            "Please report this detail:\n%s" % (_runtime_kind or "unknown", repr(_netfx_err))
        )
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, _msg, "Analogue 3D Desktop", 0x10)
        except Exception:
            sys.stderr.write(_msg + "\n")
        sys.exit(1)

_WIN_STATE = os.path.join(os.path.expanduser("~"), ".analogue3d", "desktop_window.json")
_SINGLETON_MUTEX = None     # module-level so the handle survives main() return


def _foreground_existing_and_exit():
    """On Windows, a second launch finds the running app's window and brings
    it forward instead of spawning a second WebView2 host against the same
    profile (which corrupts both)."""
    if sys.platform != "win32":
        return False
    import ctypes
    MUTEX_NAME = "Global\\auntiepickle.analogue3ddesktop.singleton"
    ERROR_ALREADY_EXISTS = 183
    global _SINGLETON_MUTEX
    _SINGLETON_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not _SINGLETON_MUTEX:
        return False
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        hwnd = ctypes.windll.user32.FindWindowW(None, "Analogue 3D Desktop")
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)      # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        return True
    return False


def _load_window_state():
    try:
        with open(_WIN_STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_window_state(state):
    # Atomic write via temp+replace so a power loss mid-write can't leave a
    # 0-byte file that wipes the user's maximized-state memory.
    try:
        os.makedirs(os.path.dirname(_WIN_STATE), exist_ok=True)
        tmp = _WIN_STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, _WIN_STATE)
    except OSError:
        pass


def main():
    if _foreground_existing_and_exit():
        sys.exit(0)
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

    # private_mode=False so theme/mode/clear in localStorage survive a restart.
    # Wipe the HTTP/Code/GPU caches on launch so a release-to-release UI update
    # isn't shadowed by cached bytes — Local Storage lives in a sibling dir.
    # Surface failures (ACL, file lock) to stderr instead of silently ignoring;
    # a stale-cache-induced UI bug would otherwise be unreproducible from logs.
    storage = os.path.join(os.path.expanduser("~"), ".analogue3d", "webview")
    import shutil
    _cache_root = os.path.join(storage, "EBWebView", "Default")
    for _sub in ("Cache", "Code Cache", "GPUCache"):
        _p = os.path.join(_cache_root, _sub)
        if os.path.isdir(_p):
            shutil.rmtree(_p, onerror=lambda f, p, ei: sys.stderr.write(
                f"warn: couldn't wipe {p}: {ei[1]}\n"))
    start_kwargs = {"private_mode": False, "storage_path": storage}
    if os.path.isfile(icon):
        start_kwargs["icon"] = icon
    webview.start(**start_kwargs)


if __name__ == "__main__":
    main()
