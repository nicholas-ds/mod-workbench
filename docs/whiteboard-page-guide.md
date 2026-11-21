# Whiteboard page guide (draft)

Status: draft, 2026-11-20. Board: `boards/done/whiteboard-page-rules` (author picked "guide plus automatic check").
The author keeps the final say on look and wording. Every look decision below carries the tag **[author to approve]**.
Scope: every HTML page an agent puts in `boards/open/*/` in any repo under `E:\repos\mods`.
Base: `docs/board-html-template.html` (clay tokens, `workbench-base-style` marker). Rules in `E:\repos\mods\AGENTS.md` still apply.

## 1. Page shape

Every page answers one question: "What must the author know or decide?" Build it in this order.

1. **Kicker**: the page kind (`Decision`, `Status`, `Report`, `Roadmap`) and the date.
2. **Title that states the point.** Write "Pick the roof for the storehouse", not "Roof options".
3. **Answer line** (first paragraph, 1 to 2 sentences): the recommendation or the result. Put it before any detail [S1, S2].
4. **Default**: one line `Default: <option>. Work continues on it if you do not answer.`
5. **Body**: options, mocks, evidence. Most important first.
6. **Next step**: one line `Next: <what happens after the answer>`.

- One decision per page. A second decision goes on a second page of the same board, with its own default.
- A status or report page has no decision. It still leads with the result and names the next step.
- Show the recommended option first, and mark it with the `Recommended` status tag.

## 2. Writing rules

- Write in ASD-STE100: active voice, one idea per sentence, 20 words maximum for an instruction, 25 for a description.
- Start each heading, paragraph and list item with its key word. Readers scan the left edge [S3].
- Use the same word for the same thing on every page and in `board.md`.
- Do not restate a list from `board.md`. The page shows what text cannot: mocks, comparison, order.
- Keep the visible text at 350 words or fewer per page (unverified limit, set by us, not by a source).
- Mark every guess "unverified". Keep each hedge at its original strength.
- Name files with a path in `<code>`. Do not paste file content.

## 3. Layout rules

| Rule | Value | Source |
| --- | --- | --- |
| Body text size | 17 px (template value), never below 16 px | [S4] [author to approve] |
| Smallest text (labels, keys, table heads) | 14 px | [S4] [author to approve]. The template uses 12 px today. |
| Text contrast | 4.5:1 or more. Large text (24 px, or 19 px bold) 3:1 or more | [S5] |
| Line length | 75 characters or fewer: `p, li { max-width: 68ch; }` | [S6] [author to approve] |
| Gap between cards | 22 px (template margin) or a grid/flex `gap` of 22 px | template [author to approve] |
| Check width | Render at 1100 px wide, as in `AGENTS.md` | AGENTS.md |
| Focal element | One per page: the answer line or the recommended option | [S3] |

Contrast facts for our tokens (computed with the WCAG formula, spot-check them before you rely on them):
`--ink` on `--card` is about 13:1 (pass). `--teal` text on `--card` is about 1.8:1 (fail).
Rule: palette hues (`--teal`, `--sienna`, `--gold`, `--blue`) are never a text color. Use them only as tints and thin edges.

At 1100 px the template body gives lines of about 110 characters. This is too long. The `max-width` rule above fixes it [author to approve].

## 4. Components

Use only these components. Do not invent new ones. Ask on a board for a new component.
Add the CSS lines below once to the template style block, under the marker [author to approve].

```css
p, li { max-width: 68ch; }
.card > h2:first-child, .card > .kicker + h2 { margin-top: 0; }
.mock { background: var(--void); color: var(--card); border-radius: 26px; padding: 16px; margin: 10px 0 6px; }
.mock .focus { outline: 3px solid var(--gold); outline-offset: -3px; }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }
.keys { font: 500 14px "DM Mono", Consolas, monospace; color: var(--ink-dim); }
.tag { background: color-mix(in srgb, var(--gold) 30%, var(--card)); }
```

**Callout**: one fact the author must not miss (vanilla basis, risk, limit).
```html
<div class="callout"><b>Vanilla basis</b>The outpost build menu, category Storage.</div>
<div class="callout warn"><b>Risk</b>Not tested in game. The claim stays unverified.</div>
```

**Option card**: one option of the decision. Kicker, title, one-line effect, mock, keys.
```html
<div class="card tint-teal"><div class="kicker">Option A · <span class="tag">Recommended</span></div>
  <h2>Filter on the rail</h2><p>One pill on top filters to mods that wait on you.</p>
  <div class="mock">...</div><p class="keys">Keys: N next decision · Enter open</p></div>
```

**Mock frame**: a drawing of a screen. Dark frame, one element with class `focus`.
```html
<div class="mock"><div class="row focus">Pick the roof</div><div class="row">Keep the rail?</div></div>
```

**Before-after**: two equal columns, the same view, one change.
```html
<div class="pair"><div class="card"><div class="kicker">Before</div>...</div>
  <div class="card"><div class="kicker">After</div>...</div></div>
```

**Status tag**: one word for a state. Allowed words: `Recommended`, `Default`, `Done`, `Running`, `Blocked`, `Unverified`, `Idea` [author to approve].
```html
<span class="tag">Blocked</span>
```

**Key list**: the keys of a mock, after the mock, in one line.
```html
<p class="keys">Keys: J/K move · Enter open · Esc close</p>
```

Comparison: for 2 to 4 options, use option cards one under the other. Use a table only when all options share the same 3 or more attributes, and keep each row on one attribute [S7].

## 5. Mock rules

- Use a real screenshot when the thing exists (a vanilla menu, our running UI). Draw a mock only for a thing that does not exist yet.
- Mark the focused state with class `focus` in every mock of an interactive screen.
- List the keys under every mock of an interactive screen (key list component).
- A game UI mock is a PNG render from the repo preview pipeline. Never put a raw SWF on a board.
- Workbench colors come from the tokens. A mock of a vanilla game screen may use game colors. Declare them as tokens `--game-*` in `:root`.
- Each option has its own mock in the same frame size, so the author compares like with like.

## 6. Automatic checks to add to `board_check.py` (proposal, do not build yet)

Each check gives one line per problem, like the current checks. "FP" is the false-positive note.

| # | Check | Precise rule | FP note |
| - | --- | --- | --- |
| 1 | Marker | Exists today: `workbench-base-style` is in the file. | None. |
| 2 | No network | No `http:`, `https:` or `//` in `src=`, `href=`, `@import` or CSS `url(`. | A URL in visible text or `<code>` is allowed. Check attributes and CSS only. |
| 3 | Real title | `<title>` is not `Board text` and not empty. | None. |
| 4 | Min text size | Every `font-size` or `font` shorthand px value is 14 or more. | Rules under `.mock` may copy small game text. Skip selectors that start with `.mock`. |
| 5 | No raw hex | No `#rgb`/`#rrggbb` outside `:root` blocks. | Game colors: allowed when declared as `--game-*` in `:root`. |
| 6 | No hue as text | No `color: var(--teal|--sienna|--gold|--blue)`. | Mock frames on `--void` may need a hue. Skip `.mock` selectors. |
| 7 | No solid fill | No `background: var(--teal|--sienna|--gold|--blue)` without `color-mix`. | Today the template `.tag` fails. Fix the template first. |
| 8 | Word cap | Visible text (tags stripped, `<style>` removed) is 350 words or fewer. | Board `mod-status` roadmap pages: cap 600. |
| 9 | Default shown | If the board has questions, at least one page has the text `Default:`. | Illustration-only items on a board with questions. Check the board, not each page. |
| 10 | One decision | A page has `Default:` at most once. | A plan page with 3 tasks is 3 decisions. Split it. Status pages that quote old defaults: allow with `Status` kicker. |
| 11 | Mock complete | Each `.mock` has a `.focus` inside and a `.keys` after it. | Static views (a render of an object): use class `mock static` to skip. |
| 12 | Inline styles | 3 or fewer `style=` attributes per page. | One-off highlights in a mock. A higher count shows a missing component. |
| 13 | No overlap | Render at 1100 px (Edge headless). Card boxes do not intersect. Vertical gap 16 px or more. No element with `scrollWidth > clientWidth`. | Needs a browser, so slow. Run on request, not on every `check`. Skip `.mock` children. |

Checks 4 to 7 read CSS with a regex. A small CSS parser class (one class, one job) is safer. Decide that at build time.

## 7. Anti-patterns in existing boards

| Anti-pattern | Where |
| --- | --- |
| Template title left as `Board text` | `mod-workbench/boards/done/ux-navigation/options.html:9`, `StarfieldCityBuilder/boards/done/next-steps/plan.html:9`, `StarfieldCityBuilder/boards/done/storehouse-dressing/progress-1.html:9` |
| Three decisions on one page | `StarfieldCityBuilder/boards/done/next-steps/plan.html:59-61` (food piles, plugin test, housekeeping) |
| Same inline patch repeated (`style="margin-top:0"`) | `next-steps/plan.html:59-61`, `storehouse-dressing/progress-1.html:59-61`. The template should own it (section 4). |
| Raw hex values in page CSS | `ux-navigation/options.html:54-59` |
| Text below 14 px | `ux-navigation/options.html:54` (13 px mock text), all pages: 12 px kicker, `th`, `.tag` from the template |
| No `Default:` line on a decision page | `ux-navigation/options.html` ("Recommended" kicker only, no default, no next step) |
| Inline outline instead of a focus class | `ux-navigation/options.html:63` (`style="outline:3px solid #deb845"`) |
| Status that goes stale ("Status: running") | `storehouse-dressing/progress-1.html:59-60` |
| Solid saturated fill against the calm rule | `docs/board-html-template.html:34` (`.tag` gold background) |
| Dead CSS: `.callout` rules overridden later | `docs/board-html-template.html:25-27` (overridden at lines 44-46) |
| 50-line style block copied into every page | every board page. Unverified fix: a shared CSS file is blocked by the board sandbox, so the copy stays. |

Good model: `ux-navigation/options.html` gives each option its own mock, marks a focus and lists keys.

## Sources

- [S1] Nielsen Norman Group, "Inverted Pyramid: Writing for Comprehension": https://www.nngroup.com/articles/inverted-pyramid/
- [S2] BLUF, Army correspondence rule AR 25-50 (summary): https://en.wikipedia.org/wiki/BLUF_(communication). Edition date unverified.
- [S3] Nielsen Norman Group, "F-Shaped Pattern of Reading on the Web": https://www.nngroup.com/articles/F-shaped-pattern-reading-web-content/
- [S4] GOV.UK Design Notes, "Making the GOV.UK Frontend typography scale more accessible" (16 px floor from British Dyslexia Association advice): https://designnotes.blog.gov.uk/2022/12/12/making-the-gov-uk-frontend-typography-scale-more-accessible. Note: WCAG sets no minimum size. The 14 px label floor is our own choice, unverified.
- [S5] W3C, "Understanding SC 1.4.3 Contrast (Minimum)": https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- [S6] Baymard Institute, "Readability: The Optimal Line Length" (50 to 75 characters): https://baymard.com/blog/line-length-readability. WCAG 1.4.8 sets 80 characters or fewer.
- [S7] Nielsen Norman Group, "Comparison Tables for Products, Services, and Features": https://www.nngroup.com/articles/comparison-tables/. Details from search summaries, full article not read (unverified).
