# Dual-mode UI redesign

Summary of the design pass on `feat/dual-mode-ui`. Captured for reviewers and future contributors who need to know _why_ the panel is shaped this way.

## Goals

1. Make the Desktop app **legible at a glance**: a non-power user should be able to plug in their console, see "everything is fine", and run a one-button update without thinking about which file went where.
2. Reduce **chrome and explanatory copy** to the hi-fi instrument register documented in [BRANDING.md](BRANDING.md).
3. Add a **picker theming system** so the app feels like a coherent product across N64 Funtastic / Analogue 3D / Pocket Glow editions, not a single skinned design.

## Two modes

### Minimal mode — the "tape deck face"

The default. A centered panel with five strata, top-down:

```
┌────────────────────────────────────────────────────────────┐
│  ANALOGUE 3D  DESKTOP        v0.2.x  [More Controls ▾]  ⚙ │
├────────────────────────────────────────────────────────────┤
│  LAST  backup just now · 87 MB                             │
├────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐ │
│  │ SD CARD  │  │ CONSOLE  │  │  CONTROLLER              │ │
│  │ ● CON…   │  │ ● UP TO… │  │  ● CONNECTED             │ │
│  │ ANALOGUE │  │  1.3.0   │  │  ◯◯◯◯  (4 ports)        │ │
│  │ E:\ · 14G│  │          │  │  2.04                    │ │
│  └──────────┘  └──────────┘  └──────────────────────────┘ │
├────────────────────────────────────────────────────────────┤
│  ▓▓▓▓▓▓▓▓▓▓▓▓ DO EVERYTHING ▸ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
└────────────────────────────────────────────────────────────┘
```

Five strata are non-negotiable:
1. **Header** — wordmark + version + mode toggle + cog.
2. **LAST line** — the most-asked question ("when did I last back up") promoted above instruments.
3. **Three instruments** — SD card / console firmware / controller status, equal-height grid.
4. **Spacer** (the white space matters).
5. **DO EVERYTHING button** — the primary action, hardware-bevelled, full-width.

### Advanced mode — the "console rack"

A rail + main grid for power users.

```
┌─────────────────┬──────────────────────────────────────────┐
│ ANALOGUE  v…  ⚙ │ ┌─ UPDATES ──┐ ┌─ BACKUPS ─────────────┐ │
│ ──────────────  │ │ CONSOLE FW │ │ BACK UP SD CARD       │ │
│ ● SD            │ │ 1.3.0 OK   │ │ Back up               │ │
│   ANALOGUE 3D   │ │ Update fw  │ │                       │ │
│   E:\ · 14G     │ │ CONTROLLER │ │ RESTORE / CLEAN       │ │
│ ● CONTROLLER    │ │ 2.04       │ │ <date> Restore Rename │ │
│   1 connected   │ │ latest Flsh│ │ Delete ▾              │ │
│ ─ RESCAN ─      │ └────────────┘ └───────────────────────┘ │
│                 │ ┌─ CART ART ─────────────────────────────┐│
│ TARGET SD CARD  │ │ <gallery>                              ││
│ ANALOGUE 3D ▾   │ └────────────────────────────────────────┘│
│ 14 GB · ★       │ ┌─ MEMORIES ─────────────────────────────┐│
│ ─────────       │ │ <game rows with state thumbnails>      ││
│  AUTO           │ │                                        ││
│  one click...   │ └────────────────────────────────────────┘│
│  DO EVERYTHING  │ ┌─ CONSOLE LOG ──────────────────────────┐│
└─────────────────┴──────────────────────────────────────────┘
```

Rail zones top-down: wordmark / device status / SD picker / Auto-hero. The Auto-hero is intentionally redundant with minimal mode — the user shouldn't lose access to DO EVERYTHING when they switch.

## Key visual changes

### N64 4-port controller indicator

Replaces the textual "controllers: 1 connected". The 4 ports are SVG circles with a stadium socket cutout and 3 contact pins, mirroring the actual Analogue 3D hardware:

```
 ╭───╮   ╭───╮   ╭───╮   ╭───╮
│ ⠘⠂  │ │ ⠘⠂  │ │ ⠘⠂  │ │ ⠘⠂  │
│  ▭  │ │  ▭  │ │  ▭  │ │  ▭  │
 ╰───╯   ╰───╯   ╰───╯   ╰───╯
   ★       ○       ○       ○
  lit     dim     dim     dim
```

Lit ports use `stroke: var(--gold)` + `drop-shadow`. Theme-specific overrides exist for White and Glow (their pale accent disappears against the dark outline — a darker glow color reads correctly).

### Funtastic translucent finish

A toggle in Settings. Layers `backdrop-filter: blur(28px) saturate(175%) brightness(1.08)` + radial gold/theme gradients over the panel so it reads as a translucent N64 Funtastic case. Layers on top of any theme — `Ice + Funtastic` looks like clear blue plastic, `Jungle + Funtastic` like green, etc.

### Theme system (10 editions)

Documented in [THEMING.md](THEMING.md). Picker lives in Settings; selection persists in localStorage.

### Demo mode

`A3D_DEMO=1 python app.py` runs the app with:
- A 132-game library, with the first 18 paired to verified `(cart_id, title)` mappings hand-identified from the labels.db so cart art _matches_ titles.
- Realistic Windows drive-letter SD path (`E:\` instead of the fake `DEMO://card/` we shipped first).
- Save-state preview thumbnails generated as scanlined+darkened+badged cart-art derivatives (no real captured frames available without a ROM).

Used during the design pass for capturing repeatable screenshots without the user's actual hardware state changing under us.

## Layout patterns that earned their place

### Stacked-stats picker

Both the minimal SD card card and the advanced TARGET SD CARD picker show:
- Short volume label as the big value (e.g. `ANALOGUE 3D`).
- Path + free-space underneath as a small mono uppercase stats line (e.g. `E:\ · 14 GB FREE`).

This came from a reviewer-driven pass after we kept seeing the selected value truncate (`E:\ [ANALOGUE 3D] (14 GB f…<chevron>`). A native `<select>` shows the same text closed and open, so the only fix was to shorten ALL option text and surface stats in a sibling line.

The selected-state never carries the size; the dropdown menu shows path+label. Stats survive on `option.dataset.freeGb` so the menu can render them if we add a custom dropdown component later.

### Bottom-anchored card actions

`.block > .grid2 > .card > :last-child { margin-top: auto }` so action buttons (Update firmware, Flash, Back up, Restore…) bottom-align across cards even when their content above varies. Without it, the visible alignment cue floats based on content height. With it, the row of buttons reads as a single instrument-panel stripe.

### Rail status — flush-left flex column

The advanced rail status box stacks each device row vertically (LED + label-above-value) instead of a horizontal grid. A 3-column grid (`LED | label | value`) was tried first; both the label and value column-aligned cleanly across rows, but the value column inherited `1fr` and stretched the label rightward, away from the LED. The flex-column with `align-items: flex-start; gap: 10px` puts the LED + label-stack as a tight left-flush group.

## Non-obvious bug fixes

These were caught in the user-feedback loop, not by reviewers:

- **`overflow: hidden` on the minimal instrument card** was clipping the lit-port drop-shadow into a square. Long-value ellipsis is already on the value element; the card-level clip was redundant. Removed.
- **`.stat:first-child { flex: 1 }` from the base style** was leaking into the advanced rail and making the first stat grow vertically (because the parent is column-flex). Overridden to `flex: 0 0 auto` in adv-rail context.
- **`.status .ghost { margin-left: auto }`** was pushing the RESCAN button to the bottom-right of the status box. Reset to `margin: 6px 0 0 0` + `width: 100%` in adv-rail context so it spans full rail width.
- **Wordmark truncated to "ANA…"** because the `@media` query keyed on viewport width but the rail is `clamp(280px, 20vw, 340px)` — a 1900px viewport can still produce a 280px rail. Solved by dropping `.adv-rail .topbar .wordmark` font to 11px / 1.2px letter-spacing so "ANALOGUE" fits in the 280px floor without media queries.

## What we deliberately did not do

- **Don't move DO EVERYTHING above the cards.** The status row is the read; the button is the action. That's the correct order.
- **Don't add a light mode now.** Every theme runs on the dark panel. A true light mode is a structural change to `--panel` and `--bg` — a separate PR. See [THEMING.md](THEMING.md).
- **Don't merge Grape and Atomic.** Both are purple, but they ship with different `--bg` values (Atomic is deeper). Documenting the duplication so a future pass can make a call rather than blindly preserving both.
- **Don't theme the green status LED.** Green is the semantic "ready/online" signal and stays fixed across all themes. Documented in CSS.

## Files touched

| File                       | Purpose                                                                  |
| -------------------------- | ------------------------------------------------------------------------ |
| `web/index.html`           | Dual-mode markup, wordmark `.thin`/`.model` spans, SD picker pattern.    |
| `web/style.css`            | Mode classes, 10 themes, Funtastic finish, instrument card layout.       |
| `web/app.js`               | Mode + theme persistence, SD picker mirroring, port-light count, demo.   |
| `demo.py`                  | 132-game library, 18 verified cart-id pairings, scanlined state thumbs.  |
| `api.py`                   | `DEMO` branches for read-only paths so the UI sees consistent state.     |
| `docs/BRANDING.md`         | The six brand pillars, voice rules, logo concept (this redesign).        |
| `docs/THEMING.md`          | Theme mechanism, the 10 themes, rules when adding an 11th.               |
| `docs/REDESIGN.md`         | This file.                                                               |
| `docs/CLI-UPDATES.md`      | Reviewer recommendations for the next CLI pass (separate PR).            |

## Outstanding (for next pass)

- True ownable 4-port app icon at all favicon sizes (sketch in BRANDING.md).
- Art caption + Memories row label-hierarchy swap (mono label above sans value).
- Wordmark `letter-spacing: clamp(…)` so glyphs don't visually drift on ultrawide.
- Decide on Atomic/Grape collapse.
