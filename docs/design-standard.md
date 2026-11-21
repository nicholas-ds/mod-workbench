# Design standard

Source: the StarExplorer project (`E:\Programs\Unity\Projects\StarExplorer`): `theme.uss`, `PlanetView.cs`, `art-backlog.md`, and the concept art. The author chose this standard on 2026-11-07 and picked the StarExplorer palette with eye-comfort tuning. Flipped and mixed variants were dropped. It starts as the standard for mod-workbench and may apply to other projects.
Implementation: `web/tokens.css` (variables) and `web/clay.css` (shapes). Visual reference: `docs/board-clay.html`.

## Rules

- All UI colors, spacing and type come from `web/tokens.css`. No hex value appears in any other file.
- A change to the palette, the scales or the shapes needs the author's approval (rule R3).
- Colors that data controls (tags, states) come from fields in files. A field names a palette entry, for example `sienna`. It never holds a raw hex value.

## Palette

Exact values from StarExplorer. The five planet colors come from `PlanetView.cs`.

| Token | Value | Source |
|---|---|---|
| `--void` | `#1E1724` | scene background, dark violet |
| `--hue-sienna` | `#D9733F` | planet, burnt sienna |
| `--hue-gold` | `#E6BA3B` | planet, ochre gold (action color) |
| `--hue-chartreuse` | `#91D94D` | planet, chartreuse |
| `--hue-verdigris` | `#5CCC6E` | planet, verdigris |
| `--hue-teal` | `#61BFA1` | planet, teal |
| `--signal-cyan` | `#66D9F2` | probe |
| `--signal-amber` | `#F2B34D` | ferry |
| `--star-cream` | `#FFEDAD` | star, text on dark |

## Clay colors (locked, 70% vibrancy)

The table above holds the exact StarExplorer values. The author tuned the clay colors to 70% vibrancy. That is 70% of the way from the eye-comfort set (`docs/eye-comfort.md`) to the original colors. Dark ink text on each reaches 4.8:1 or higher.

| Token | Value | Hue from |
|---|---|---|
| `--clay-rail` | `#5fc670` | verdigris |
| `--clay-whiteboard` | `#62ba9e` | teal |
| `--clay-questions` | `#d27648` | sienna |
| `--clay-gold` | `#deb845` | gold |
| `--clay-tag` | `#e9af53` | amber |
| `--clay-info` | `#68d0e8` | cyan |
| `--clay-green` | `#90d152` | chartreuse |
| `--clay-card` | `#ebe5cb` | star cream |
| `--color-text` | `#e0dac2` | star cream |

Accents are the complements at the same vibrancy: `--accent-on-void` `#90d251`, `--accent-on-sienna` `#47a4d3`, `--accent-on-teal` `#c2708a`, `--accent-on-verdigris` `#c761b6`.

Changing the vibrancy needs the author's approval.

StarExplorer rule kept: authored colors must not be tone-mapped or desaturated. The UI uses plain sRGB values.

## Complementary colors (general rule)

StarExplorer is the base. The UI uses only the base colors and their complements. A complement is the base color rotated 180 degrees in hue, with the same lightness and saturation. Every new color must be one of these. No other hue is allowed.

| Base | Complement |
|---|---|
| `--void` `#1E1724` (violet) | `#91D94D` (chartreuse, the game's direct complement of the background) |
| `--hue-sienna` `#D9733F` | `--comp-sienna` `#3FA5D9` (blue) |
| `--hue-gold` `#E6BA3B` | `--comp-gold` `#3B67E6` (indigo) |
| `--hue-chartreuse` `#91D94D` | `--comp-chartreuse` `#954DD9` (violet) |
| `--hue-verdigris` `#5CCC6E` | `--comp-verdigris` `#CC5CBA` (orchid) |
| `--hue-teal` `#61BFA1` | `--comp-teal` `#BF617F` (rose) |
| `--signal-cyan` `#66D9F2` | `--comp-cyan` `#F27F66` (coral) |
| `--signal-amber` `#F2B34D` | `--comp-amber` `#4D8CF2` (blue) |

How to use it:
- A surface and its accent are complements. Accent examples: blue on a sienna panel, orchid on a verdigris rail, chartreuse on the void table.
- Buttons, selected rows and default options on a surface use that surface's accent (`--accent`).
- Check text contrast on each accent before use. Dark ink text must stay readable.

## Modes

- **Dark** is the only theme. The surface is `--void`. Text is `--star-cream`. There is no light theme.
- **Greyscale** is a toggle for tired eyes. It removes all color and keeps shape and light.
- Color is welcome, but it must not strain the eyes.

## Spacing and type

Same scale as StarExplorer.

- Spacing: 2, 4, 8, 16, 32 px (`--space-xs` to `--space-xl`).
- Type sizes: title 22, body 16, hint 13, report 12 px.
- Fonts: Baloo 2 for titles, Nunito for text, DM Mono for small labels.
- Scrims: `rgba(0,0,0,0.6)` and `rgba(0,0,0,0.5)`.

## Shapes and light

- Surfaces are clay: lumps with uneven outlines (eight-value border radius), fine grain, and a lit top left.
- StarExplorer light rig: one key light, one fill, dim ambient. The shadows imitate it.
- Raised clay means "you can press this". A pressed-in well means "this holds content" (image slots, text fields).
- Concept art (`concept-art/`) shows inked, cracked outlines and watercolor washes. This is reference only. It is not a token yet.

## Motion

- Stop-motion wobble: three held poses, about 0.35s in total. It plays once on hover and once on press. It never runs constantly.
- To wobble any element from a script, add the `.wobble-once` class. Remove the class when the animation ends.
- It turns off when the system asks for reduced motion.

## Layout

- The whiteboard gets most of the screen: about 70% of the width. Questions get about 30%, with a minimum width of 300 px.
- Use the full window width. Keep gutters small (16 to 24 px). Do not center content in a narrow column.
- The whiteboard is one large 16:9 view. It is the largest 16:9 area that fits the window. It shows one item at a time. A row of caption buttons switches items (pages). Never show several items in a grid.

## Controls

- No hard outlines anywhere. Shape comes from soft light and shade, like inflated clay.
- Every button is a puffy lump with a solid fill. The main action is gold. Other buttons are cream.
- A pressed or selected button turns gold and sinks in.
- Text fields are a light cream with dark text and a clear placeholder. Never use dark text on a dark well.
- Keyboard keys are puffy cream caps with dark text.
- Hint text on clay is full ink, not a dim color.

## Contrast

- Text on clay uses `--color-ink` (the void color). It must stay readable on every clay color.
- Check any new clay color against `--color-ink` before it enters the palette.

## Themes (author request, 2026-11-12)

Two themes share one set of hues. Classic is the default values in `web/tokens.css`. Calm is the last block of `web/tokens.css` (`data-theme="calm"`): less saturation on large areas, a softer highlight. The header buttons "classic" and "calm" switch them and the choice is stored in the browser. The message dock keeps classic colors in both themes (class `theme-classic`). Details and numbers: `docs/color-value-principles.md`.
