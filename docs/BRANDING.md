# Brand language

> Reference for anyone designing, copywriting, or contributing UI to Analogue 3D Desktop. Use these pillars when judging trade-offs — if a pattern in this doc conflicts with what you're proposing, the burden is on the proposal.

## What we are

A desktop utility for a hi-fi retro console. The visual register is **instrument-panel**, not dashboard. Hardware metaphor is structural, not decorative. Reference anchors: Analogue Inc., Teenage Engineering OP-1, Bowers & Wilkins, Nothing.

## Six pillars

### 1. Instrument panel, not dashboard
Every element should look like it _does_ something or _measures_ something. The eye should read each card as a discrete control surface, like the front of an amplifier. Avoid: depth shadows, gradients (except the Funtastic translucent finish, which is texture not chrome), rounded corners above 4px, drop-shadowed text, "card" hover animations that float-up.

### 2. Mono labels → sans values
The hi-fi instrument read comes from pairing two type registers:

| Role             | Family | Case      | Size      | Letter-spacing | Color           |
| ---------------- | ------ | --------- | --------- | -------------- | --------------- |
| Technical label  | mono   | uppercase | 10–11px   | 2–3px          | `--gold`        |
| Status word      | mono   | uppercase | 10–11px   | 1.5–2px        | `--dim`         |
| Data value       | sans   | natural   | 13–36px   | normal         | `--text`        |
| Description text | sans   | natural   | 12–13px   | normal         | `--dim`         |

Reverse this and the panel reads as a generic web form. The pattern is `LABEL → VALUE`, never `value → label`.

### 3. One accent at a time
There are exactly three accent budgets, and they don't mix on the same control:

- `--gold` / theme accent — the **selected**, **navigable**, or **attention** state. Borders, lit LEDs, primary buttons, picker chevrons.
- `--green` — system semantic: **online / ready / connected**. Never themed, by design. Documented in `style.css` so it isn't "fixed" by accident.
- `--red` — semantic: **danger / delete / destructive**. Never used decoratively.

Theme dots in the picker carry the saturated accent. Everything else in the UI obeys the same restraint as the rest of the panel — even on Watermelon, the chrome shouldn't read as a "red app".

### 4. Assume competence
Buttons are imperative, copy is minimal, no hedging. The reader is competent — they bought a $499 console and a labels.db.

| Don't                                | Do                       |
| ------------------------------------ | ------------------------ |
| "Please confirm this action"         | "Confirm"                |
| "Click here to backup your card"     | "Back up"                |
| "Are you sure you want to delete?"   | "Delete?"                |
| "Accent color inspired by the N64…"  | "N64 console colors."    |
| "Funtastic — translucent finish"     | "Funtastic"              |

Buttons explain themselves through register (mono, uppercase, hardware-bevel). Don't undercut a strong button with an explanation paragraph above it.

### 5. Scale fluidly
Layout and type both use `clamp(min, viewport-relative, max)` so the same hierarchy holds at 900px, 1400px, and 3840px. Specific patterns:

- Panel width: `clamp(1400px, 78vw, 2400px)` — fills ultrawide intentionally, has a floor on narrow.
- Font sizes that need to read at every scale use `clamp(min, ~1vw, max)` so the cap-height tracks the panel.
- Letter-spacing on display type also clamps: `clamp(1.5px, .15vw, 2.5px)` so glyphs don't visually float apart on ultrawide.
- At narrow widths, hide subtitles and decorative text before truncating the primary wordmark.

### 6. Hairline precision
- All borders are 1px and use `--gold-line` (rgba accent at ~35% opacity, .32 for pale themes White/Smoke/Glow).
- Icons (LEDs, ports, chevrons) are stroke-based. Fill only when active.
- The Funtastic translucent finish is the **only** sanctioned "depth" treatment. Other shadows are bug.

## The wordmark

```
ANALOGUE 3D  DESKTOP
^^^^^^^^^^^  ^^^^^^^
mono 700      mono 400
gold          dim
ls 2px        ls 4px
```

- Primary: `ANALOGUE 3D` in gold, mono 700, the lead unit.
- Subtitle: `DESKTOP` in dim, mono 400, with wider letter-spacing so it reads as a technical descriptor not a marketing tagline.
- At narrow widths the wordmark hides `DESKTOP` first, then `3D` (`.thin` and `.model` spans in HTML for surgical control), then shrinks the font. It never truncates with an ellipsis mid-word.
- For brand carriers (taskbar icon, splash, packaging) the icon does the lifting — see the icon concept below.

## Logo / icon concept

The 4-port indicator is the most ownable mark. It is already in the UI at `#minCtrlPorts` and reads at every size:

- **16×16 (favicon)** — Four small dots in a row, one lit. Functional silhouette only.
- **32×32 (taskbar)** — Four circles with the stadium socket cutout, one with gold glow.
- **1024×1024 (app icon)** — Full SVG with circles, stadium sockets, three contact pins per port, port-1 lit. Faint Funtastic halo around the whole mark for the casing feel.

Avoid: photorealistic console renders, "3D" volumetric typography, lockups that pair the wordmark with a different icon (the wordmark IS one mark; the 4-port IS the other).

## Brand voice in errors and tooltips

The same imperative-minimal register as buttons. Errors should name the problem, not explain it.

| Bad                                                            | Good                                              |
| -------------------------------------------------------------- | ------------------------------------------------- |
| "Sorry, we couldn't find an Analogue 3D SD card."              | "No Analogue 3D card detected. Pick one above."   |
| "The firmware download appears to have failed."                | "Firmware download failed. Retry?"                |
| "It looks like the controller isn't currently connected."      | "Controller not connected."                       |

Never lead with "Oops" / "Sorry" / "Hmm". The product doesn't apologize for itself.

## Quick gut-check before merging

If a contribution adds a new visual element, ask:
1. Does it look like part of an instrument, or part of a web app?
2. Is the label mono-uppercase and the value sans?
3. Did you introduce a second accent color on chrome?
4. Did you write copy your reader needed to be talked through?
5. Does the layout hold at 900px AND 3840px?

If any answer is "no" or "I don't know", the pattern needs revision before merging.
