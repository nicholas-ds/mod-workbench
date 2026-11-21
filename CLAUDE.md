# CLAUDE.md: mod-workbench

Local desktop platform on top of the Starfield mod repos. Read `docs/design.md` and `docs/game-testing.md` before you change anything. The plan is in `docs/superpowers/plans/`.

## Architecture standards (enforced)

These add to the user-level standards. They are not suggestions.

- **Classes.** One responsibility per class. The name states the job (`CardRepository`, `QueueSorter`). No `Manager`, `Helper`, `Utils`.
- **Functional inside classes.** Methods take parameters and return values. No hidden state. Use frozen dataclasses for data. Side effects (disk, network, toast, process) live in edge classes only.
- **Pipelines.** A multi-step process is one method. Each line calls one named method and passes a named value to the next line. No loose dicts or tuples between steps. No nested calls.
- **Types.** Annotate every signature. Pass named types between steps, not `dict` or `Any`.
- **Dependencies.** Inject through constructors. Dependencies point from the edge to the core.
- **Size.** A file has 250 lines or fewer. A class that needs "and" to describe it must split.
- **Tests.** Test-driven. One test file per class. Tests name the behavior.

Example of the required pipeline shape:

```python
raw_text = self.card_reader.read(path)
front_matter = self.front_matter_parser.parse(raw_text)
card = self.card_builder.build(front_matter)
```

## Project rules

- R1. Plain files in mod repos are the source of truth. No private database.
- R2. Agents never wait for the author. They write a decision card and continue on the default.
- Hard rules (author actions on a board, reply in the workbench UI, master tracking, one task per session with `/handoff` then `/clear`) are in `E:/repos/mods/AGENTS.md`.
- R3. Agents never make a UI decision. They write a card and stop that work.
- R4. The workbench hardcodes no vocabulary. Tags, columns, labels and colors come from files.
- R5. Asset work sits behind a files-in, files-out interface so Rust can replace Python.
- R6. Only the orchestrator launches or tests the game. Tests use a fresh copy of the frozen baseline in the test slot. Never load the main save.
- R7. Each layer is useful alone.
- R9. Mod designs stay inside vanilla Starfield. Use vanilla assets, or generate assets in the vanilla style. Take cues from existing vanilla styling and mechanics. Anything outside vanilla is a board question, with the vanilla option as the default.
- R8. Build so Rust can plug in later. Do not write Rust now. Keep any part that may become Rust behind a boundary of plain data:
  - The boundary is a command line program or a file. Input and output are files and JSON. No Python objects, pickle, or shared memory cross it.
  - Boundary data types are frozen dataclasses that map one to one to JSON. Use only str, int, float, bool, list, and dict with string keys.
  - File formats (cards, status, config) stay language-neutral: TOML, YAML front matter, JSON, Markdown.
  - A class behind a boundary takes and returns boundary types only. It hides parsing, I/O and format details. Callers never see them.
  - A contract test suite checks each boundary with sample files. Any implementation (Python or Rust) must pass the same suite.
  - Do not add abstract base classes for this until a second implementation exists. The boundary itself (CLI + JSON) is the interface.

## Design standard

- The UI follows `docs/design-standard.md`. It comes from the StarExplorer project: its palette, spacing, type and clay shapes.
- All colors, spacing and type come from `web/tokens.css`. Shapes come from `web/clay.css`. No hex value outside `tokens.css`.
- Use only StarExplorer colors and their complements (hue rotated 180 degrees). A surface and its accent are complements. No other hue.
- Dark only. There is no light theme. Greyscale is an option for tired eyes.
- A change to the standard needs the author's approval.
- **Whiteboard text pages use the clay base style (hard rule, author, 2026-11-08).** Any whiteboard page that is not a screenshot of something real (text, tables, diagrams as HTML) must be built from `mod-workbench/docs/board-html-template.html`: clay cards, tokens, the style marker. Plain text on white is a defect. Calm colors only: cream page and cards, palette hues only as light tints or thin edges, never solid saturated fills. `python -m workbench check` rejects an HTML item without the marker. Every new workbench element or feature is styled from `web/tokens.css` and `web/clay.css`.

## Worker task size (enforced)

Give each GLM worker a small, scoped task. See `LESSONS.md`.
- One kind of change per task. Name 3 to 5 files to edit.
- Do not tell a worker to read large files. Put the needed values in the brief.
- An empty reply or `finish: length` means the task was too big. Split it. Do not retry the same brief.
- Design and CSS decisions stay with the orchestrator.

## Design review gate

GLM workers are weaker at visual design. The orchestrator has the final say on every UI change.
- After a worker changes anything under `web/`, take screenshots of the running page (Playwright with Edge: home, board view, at 1500 and 1920 px wide). Compare them with `docs/board-clay.html`.
- Grade each area from A to F: layout and proportions, color and accents, shapes and shadows, type and spacing, controls, contrast and legibility, fit to the design standard.
- Send the worker the grades and exact fixes for every area below B. Repeat until all areas are B or better.
- Only then report the UI as done.

## Workflow

- Python is `.venv/Scripts/python`. Run tests with `.venv/Scripts/python -m pytest`.
- Use GLM workers (the `opencode-agent` skill) for all work that fits: coding, tests, refactors, docs, research. They cost less. Do the work yourself only for decisions, review, and small orchestration. Start sessions with `-NoWatch`.
- Workers (OpenCode GLM) never run `git commit` or `pip install`. The orchestrator commits after review.
- All chat text follows ASD-STE100 (user CLAUDE.md).


- **One subject, one board (author, 2026-11-20).** See root `AGENTS.md`. Add to the existing board of a subject. Do not raise a second one.
