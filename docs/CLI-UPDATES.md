# CLI updates — recommendations for the next pass

Captured from two parallel reviewer agents during the Desktop redesign so the CLI can land the same brand language without forgetting what was flagged. **This file is a roadmap, not implemented.** The actual CLI changes belong in a separate PR against the [Analogue 3D Utility](https://github.com/auntiepickle/Analogue3DUtility) repo.

The reviewers were asked to apply the brand pillars from [BRANDING.md](BRANDING.md) to the CLI surface: instrument panel not dashboard, imperative copy, hairline precision.

## Voice & copy fixes (high-confidence, ship first)

1. **Replace "This will, for every part that applies:"** in the Auto-mode preamble with `ui.info("Backup will:")`. The hedged phrasing breaks the imperative register.
2. **Standardize menu labels to short imperative.** "Update the 8BitDo 64 controller" → "Flash controller". "Back up your SD card" → "Back up". Match the GUI's button voice.
3. **Replace restore confirmation `"WARNING: This will OVERWRITE files...\nType YES to continue"`** with `ui.confirm("Overwrite Library/Settings/Memories?", default=False)`. The all-caps shout + multi-line block breaks tone. The product trusts the user.

## Affordances missing vs. the GUI

4. **Pre-flight check before Auto.** Today the CLI confirms once then runs. Mirror the GUI's status row: print a 4-line summary (SD path + free space, controller count, console FW version, latest available) before the confirm. If anything's red, name it before asking.
5. **Progress bars on long operations.** `sdcard.create_backup()` accepts a `progress` callback that the CLI doesn't pass. Wrap backup-zip, firmware download, and art-pack install in Rich `Progress` (determinate where bytes are known, spinner where they aren't). The flash flow already has a progress callback — extend the same pattern.
6. **Actionable error messages.** Raw `ControllerError: no response to cmd 0xC3` is a stack trace masquerading as feedback. Wrap engine errors in structured `{ok, error, hint}` so the user sees "Controller not responding. Reseat the cable and rescan." instead of an opcode.

## Surface shape (medium-confidence, design before shipping)

7. **Subcommands + zero-arg menu.** `a3d` with no args → interactive menu (mirrors GUI's Minimal mode). `a3d backup`, `a3d update`, `a3d auto`, `a3d flash <port>` for scripting and power use. The current flat menu makes Power-User affordances harder to discover.
8. **`--json` flag.** Emit newline-delimited JSON for each step under any subcommand. Lets users pipe `a3d auto --json` into a CI run, a home automation hook, or a dashboard.
9. **One-shot art pack install.** `a3d artpack` should install the community pack with no prompts. Source-picker / URL flow is for `a3d artpack --custom <url>`. The current 5-step prompt sequence violates "assume competence".

## Optional but high-payoff (defer to a follow-up)

10. **`a3d tui` (Textual live dashboard).** Mirrors the Desktop's Advanced mode in the terminal — live LED status, controller port row, firmware version diff, hotkeys (`u` = update fw, `b` = backup, `f` = flash). Keeps the same "instrument panel" mental model across surfaces. Separate from the CLI subcommand surface so JSON output isn't fighting an interactive UI.
11. **Config persistence at `~/.analogue3d/config.json`.** Default SD card path, default art pack source, last-used label. After first run, `a3d auto` just works on the same card without re-detecting.
12. **Auto-detect with override.** Score SD card candidates (label match, free space, file structure). Single obvious card → proceed silently. Multiple → prompt. `--card <path>` to skip detection entirely.

## What NOT to change

- **Color/output for piped runs.** Detect TTY; strip ANSI when stdout isn't a terminal. The current behavior is probably fine — verify before changing.
- **The `a3d` command name.** Short, owned, already in muscle memory. Don't rename.
- **Backup zip format.** Sister projects (GUI, future TUI) read these. Schema is shared.

## Why all of this

The Desktop redesign committed to a single brand language across modes. The CLI is the third surface (after Minimal and Advanced) and currently feels like an unrelated product. Landing items 1–6 above gets it ≥80% aligned. Items 7–9 make it _intentional_. Items 10–12 make it _premium_.

Suggested PR sequence:
- **PR 1 (small)**: Voice + copy fixes 1–3 + progress bars (#5). Half-day of work.
- **PR 2 (medium)**: Pre-flight check (#4), actionable errors (#6), `--json` flag (#8). Couple of days.
- **PR 3 (larger)**: Subcommand restructuring (#7), one-shot art pack (#9), config persistence (#11).
- **PR 4 (optional, separate)**: `a3d tui` (#10). Textual dependency, larger scope.
