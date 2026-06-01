# Contributing to Analogue 3D Desktop

Issues and pull requests are welcome. A few notes so we stay aligned.

## Before opening a PR

- **Read [docs/BRANDING.md](docs/BRANDING.md).** Six brand pillars + voice rules. New UI work should fit, or come with a clear argument for why a pillar doesn't apply.
- **If your PR touches themes**, read [docs/THEMING.md](docs/THEMING.md). The token system has invariants (`--gold-soft` lighter than `--gold`, `--gold-dim` ≥30% luminance drop, etc.) — break them and panels go dim in the picker or vanish on White/Glow.
- **If you add a new visual element**, the quick gut-check at the bottom of BRANDING.md is the same one we use in review.

## Testing

- The Desktop app runs with `python app.py`. Requires `pywebview` + `analogue3d` (`pip install -e ../Analogue3DUtility` for local dev).
- For UI changes you can't test against your own hardware, run in demo mode: `A3D_DEMO=1 python app.py`. Demo mode shows a synthetic library + scanlined save-state thumbnails so the layout has realistic density.
- For theme work: `A3D_THEME=jungle python app.py` (or any of the 10 theme IDs in `web/app.js#THEMES`) launches with that theme pre-selected via URL hash, no localStorage manipulation needed.
- For advanced-mode screenshots without clicking: `A3D_MODE=tinker A3D_DEMO=1 python app.py`.

## Voice

Imperative, minimal, hi-fi instrument-panel register. The bad/good table in BRANDING.md is the reference. "Confirm" not "Please confirm". "Back up" not "Click here to back up your card".

## Code style

- JavaScript: small functions, named constants for selectors (`el.x` pattern), `console.warn` on swallowed errors instead of empty `catch(e){}`.
- CSS: hairline 1px borders, theme accents through `var(--gold-*)`, no hardcoded color literals on chrome.
- Python: match the rest of the engine — short docstrings, structured returns for action methods.

## Reporting issues

- Screenshots in 1+ themes help — `A3D_THEME=...` makes this easy.
- Window width + DPI scaling — a lot of past layout bugs only show at narrow widths or high DPI.
- For demo-mode bugs vs real-hardware bugs, please say which.

## CLI updates

The CLI is a sibling project in [Analogue 3D Utility](https://github.com/auntiepickle/Analogue3DUtility). [docs/CLI-UPDATES.md](docs/CLI-UPDATES.md) captures reviewer recommendations from this redesign pass for a future CLI update — start there if you want to land matching brand language in the CLI.
