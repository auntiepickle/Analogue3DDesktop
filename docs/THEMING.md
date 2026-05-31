# Theming

Mechanism, palette, and rules for the 10 accent themes + Funtastic translucent finish.

## How a theme works

Every theme is a body class that overrides a fixed set of CSS custom properties. The rest of the UI references those properties — change the theme, the whole panel re-tints.

```css
body.theme-jungle {
  --gold:       #3fcb6b;                        /* primary accent — labels, lit LEDs, primary buttons, picker chevrons */
  --gold-soft:  #6fdf90;                        /* hover / active brighter; MUST be lighter than --gold */
  --gold-dim:   #1e8a44;                        /* dim text / secondary accent on dark panel — drop ~30% luminance from --gold */
  --gold-line:  rgba(63,203,107,.38);           /* hairline borders, .38 is the default opacity (.32 for pale themes) */
  --gold-faint: rgba(63,203,107,.12);           /* faint backgrounds / Funtastic case-glow tint */
}
```

The tokens are named `--gold-*` for historical reasons (the default theme is gold). They act as accent slots regardless of theme.

Themes do NOT override:
- `--text`, `--dim` — neutral typography colors. Same across all themes for legibility discipline.
- `--green`, `--red` — semantic status colors. Green is "connected/online" by design and never themed.
- `--bg`, `--panel`, `--panel-2` — surface colors. Themes inherit, except `--bg` is intentionally over-tinted on Atomic so it reads as the iconic deep purple console.

## The 10 themes

| ID         | Accent       | Edition                                                                     |
| ---------- | ------------ | --------------------------------------------------------------------------- |
| gold       | `#e8b923`    | Analogue 3D default — charcoal-and-gold                                     |
| white      | `#f0eee6`    | Analogue 3D White edition                                                   |
| glow       | `#c4f070`    | Analogue Pocket Glow series                                                 |
| ice        | `#58c7e3`    | N64 Funtastic Ice Blue                                                      |
| jungle     | `#3fcb6b`    | N64 Funtastic Jungle Green                                                  |
| watermelon | `#ff5b6b`    | N64 Funtastic Watermelon Red                                                |
| grape      | `#a663ff`    | N64 Funtastic Grape Purple                                                  |
| fire       | `#ff7430`    | Pocket Fire                                                                 |
| atomic     | `#b066ff`    | N64 Atomic Purple (deeper bg variant)                                       |
| smoke      | `#cfd1d5`    | N64/Pocket Smoke clear                                                      |

## The Funtastic finish

`body.clear` is the translucent-case overlay. It's orthogonal to theme — any theme + `clear` reads as that theme's casing color in translucent form (`ice + clear` = blue-tinted glass, `jungle + clear` = green, etc.).

Mechanism:
- Boosts `--gold-faint` and `--gold-line` opacity via `color-mix()` so the case glow holds.
- Lays radial gradients + repeating noise on the background so the bg reads as plastic.
- Switches the panel background to a translucent `color-mix(in oklab, var(--panel) ~40%, transparent)` + `backdrop-filter: blur` for the frosted-glass effect.

Pale themes (White, Smoke) need their `--gold-faint` boosted further when Funtastic is on, otherwise the halo washes out on the dark bg. Specific overrides live near the Funtastic block.

## Rules when adding a theme

If you add an 11th theme, you must:

1. **`--gold-soft` strictly lighter than `--gold`.** Smoke was originally inverted (soft `#e6e7ea` was paler than gold `#cfd1d5` by ≥10 luminance points). The hover/active state is supposed to be _more_ accent, not _less_. Increase luminance by 8–10 points perceptually.

2. **`--gold-dim` drops ~30% luminance from `--gold`.** Otherwise dim text vanishes on `--panel`. White was originally too-bright (`#b8b6ad`); we dropped to `#8a8884`. Glow needed desaturation AND darken to `#5a7a2e`. Sanity check: open a chrome devtools and verify dim text has contrast ratio ≥ 4.5 against `#16161a`.

3. **`--gold-line` opacity is `.38`** for saturated themes, `.32` for pale themes (White, Smoke), `.34` for marginal (Glow). The reason: pale accents at `.38` create visual noise on the panel; reducing border opacity preserves the "hairline precision" pillar.

4. **Lit-state on light themes needs an explicit override.** `drop-shadow(0 0 3px var(--gold))` is invisible on the dark port outline when `--gold` is `#f0eee6`. Add a theme-specific override that uses a DARKER glow color so the lit state still reads:

   ```css
   body.theme-yourtheme .n64-ports .port.lit .port-ring,
   body.theme-yourtheme .n64-ports .port.lit .port-socket {
     stroke: #darker-color;
     filter: drop-shadow(0 0 5px #darker-color);
   }
   ```

5. **Register the theme in `app.js`.** Add an entry to the `THEMES` constant:

   ```js
   { id: "yourtheme", name: "Your Theme", dot: "#hex" },
   ```

   The theme picker iterates this list; without an entry, the user can't pick it.

6. **Test with Funtastic on AND off.** Some themes look fine on the dark `--bg` but the Funtastic blur changes the contrast math.

## Atomic-Grape consideration

Both are purple. Atomic is brighter and ships with a deeper `--bg`. If the picker feels like it has two "purple" picks, the cleaner move is to drop Atomic OR re-anchor it as a distinctly _violet/indigo_ accent (e.g. `#9b65ff` with a true-blue undertone). Documenting the duplication so the next contributor can make a call rather than blindly preserving both.

## What about a light mode?

There isn't one. Every theme runs on the dark panel + dark bg. White is "light accent on dark UI", not light mode.

If you want a true light theme:
- Add a separate `body.light` orthogonal class (not a theme) that overrides `--panel`, `--panel-2`, `--bg`, `--text`, `--dim`.
- All themes should still work layered on top.
- Plan to redo the Funtastic finish — the radial-gradient + blur math assumes dark.

That's a larger structural change than a theme add — call it out in the PR description.
