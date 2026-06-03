# Known issues — Windows runtime & packaging

This document tracks the Windows-specific startup failures we are solving on the
`fix/netfx-arm64` branch, what causes each, and the state of the fix. All of
these manifest as the app failing to launch (a dialog, then exit) — none are
logic bugs in the app itself.

---

## 1. pywebview silently downgrades to CoreCLR → `System.Object` TypeLoadException

**Symptom**

```
System.TypeLoadException: Could not load type 'System.Object' from assembly
'System.Private.CoreLib, Version=9.0.0.0' because the parent does not exist.
  ... at webview/platforms/winforms.py, class OpenFolderDialog (load time)
```

**Root cause**

pywebview's WinForms backend (`webview/platforms/winforms.py`) opens with:

```python
try:
    import clr
except Exception:
    os.environ['PYTHONNET_RUNTIME'] = 'coreclr'   # silent downgrade
    import clr
```

If the *first* `import clr` throws for **any** reason, pywebview hard-forces
**CoreCLR** (.NET 5+). CoreCLR then resolves a .NET 9 WinForms assembly whose
parent, `System.Private.CoreLib 9.0.0.0`, can't be bound on a machine without a
usable .NET *Desktop* Runtime — producing the TypeLoadException at class-body
load time. (`System.Private.CoreLib` is CoreCLR's corelib; .NET Framework's is
`mscorlib` — its presence in the trace proves CoreCLR was active.)

**Why v0.3.1 didn't fix it**

v0.3.1 only set `os.environ.setdefault("PYTHONNET_RUNTIME", "netfx")`. That is an
env-var *request* that pywebview's `except` block simply overwrites (and
`setdefault` is a no-op if the var is already set). The app never loaded clr
itself, so nothing locked the runtime before pywebview ran. It is structurally
incapable of preventing the downgrade.

**Fix (`app.py`)** — *done*

Force netfx and **load it ourselves, before importing webview**:

```python
os.environ["PYTHONNET_RUNTIME"] = "netfx"   # hard set
import pythonnet
pythonnet.load("netfx")   # raises if .NET Framework / the netfx shim is unavailable
import clr                # no-op now
```

A successful `load("netfx")` sets `pythonnet._LOADED = True`, so pywebview's
later `import clr` is a cached no-op that **cannot throw** — its coreclr branch
becomes unreachable. If netfx genuinely can't load, we **fail loudly** with a
MessageBox (the build is `--windowed`, so stderr is invisible) and exit, instead
of degrading to a broken CoreCLR with an unactionable error.

Verified with a 3-way harness (simulating a machine where netfx can't load):
- old code → forced to CoreCLR, winforms import crashes (the bug);
- new code, netfx broken → caught cleanly, clear message, never touches CoreCLR;
- new code, netfx healthy + env adversarially poisoned to `coreclr` → stays on
  .NET Framework, winforms imports fine.

---

## 2. Smart App Control / WDAC blocks the unsigned one-file exe → "Bad Image"

**Symptom**

```
Analogue3DDesktop-windows.exe - Bad Image
C:\Users\...\AppData\Local\Temp\_MEInnnnnn\ucrtbase.dll (or python313.dll) is
either not designed to run on Windows or it contains an error.
Error status 0xc0e90002.
```
…and the underlying bootloader error:
```
Failed to load Python DLL '...\_MEInnnnnn\python313.dll'.
LoadLibrary: An Application Control policy has blocked this file.
```

**Root cause**

The release exe is built with PyInstaller `--onefile`, which at launch extracts
its bundled DLLs to a `%TEMP%\_MEInnnnnn` folder and `LoadLibrary`s them. Those
DLLs are **unsigned**. **Smart App Control** (Windows 11, on by default on many
new machines — especially ARM64 Copilot+ PCs) and/or a **WDAC** code-integrity
policy refuse to load unsigned binaries, surfacing as a generic "Bad Image"
(`0xc0e90002`). This happens in the bootloader, *before* Python starts — it is
**not** ARM64-specific and is **unrelated to the netfx issue above**.

> Note: this was initially misdiagnosed as UPX compression. A non-UPX rebuild
> failed identically, and dialog text "An Application Control policy has blocked
> this file" identifies the real cause. UPX is still disabled (see issue 3).

**Fix — *in progress / decision needed***

The robust fix is to **code-sign the Windows binaries** (the macOS build is
already signed/notarized in `release.yml`; the Windows job currently does no
signing). A reputable certificate (EV gives instant SmartScreen/SAC reputation)
lets the signed exe pass Smart App Control. Secondary mitigations:
- `--onedir` instead of `--onefile` (DLLs sit on disk next to the exe rather
  than being extracted to `%TEMP%` at runtime);
- developer testing: **run from source** under trusted system Python, which SAC
  permits (this is how we test the netfx fix on ARM64 — see `docs/` testing
  notes), or temporarily evaluate with SAC off on a throwaway test machine.

---

## 3. UPX compression — disabled (ruled out as a cause, kept off defensively)

`build.py` now passes `--noupx` and the (untracked) spec uses `upx=False`.
PyInstaller auto-uses UPX whenever it's on `PATH` (it is on GitHub's
`windows-latest` runner), so the *released* binary was being compressed even
though local builds weren't. UPX was **not** the cause of the Bad Image (issue
2), but packed binaries are more likely to be flagged by SAC/SmartScreen/AV and
UPX has its own ARM64 quirks, so we keep it off. Size cost: ~29 MB → ~42 MB.

---

## 4. CI installs runtime deps unpinned (reproducibility hazard)

`.github/workflows/release.yml` runs `pip install pywebview pythonnet` with no
version pins, and `requirements.txt` doesn't pin `pythonnet`/`clr-loader` at all.
The released artifact can therefore drift from the tested combination
(`pywebview 6.2.1`, `pythonnet 3.1.0`, `clr-loader 0.3.1`). Recommended (not yet
applied): pin those three in both `requirements.txt` and `release.yml`, plus
`pyinstaller`. This isn't the current crash, but it prevents a future one.

---

## ARM64 — open question

Once the trust block (issue 2) is bypassed by running from source, the open
question is whether **netfx loads on Windows-on-ARM** (under x64 emulation).
- If yes → the only ARM64 blocker is code-signing (issue 2); ship a signed x64
  build that runs under emulation.
- If no → netfx is unavailable on ARM64 (clr_loader ships no arm64 `ClrLoader.dll`);
  the app.py fix shows a clear message, and real ARM64 support requires bundling
  a self-contained .NET Desktop Runtime and using coreclr, or an ARM64-native build.
