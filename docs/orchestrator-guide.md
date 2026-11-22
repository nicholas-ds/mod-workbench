# Orchestrator guide

For orchestrators and workers in the build workspace and the research workspace. Read this before you ask the author a question or show the author something.

## The rule

The author does not read code and does not wait for you to ask in chat. You show things and ask questions on a **board**. The author answers in the workbench (`python -m workbench serve`, then open `http://127.0.0.1:8760`).

- You never wait for an answer. Every question has a default. Continue on the default.
- You never decide anything the author sees: layout, look, flow, or a name. Show a board and ask. Do not start the work that depends on the answer. Do other work.
- You surface work before the author asks: plan, designs, findings and open items go on a board in the same turn. See `E:/repos/mods/AGENTS.md`, "Surface work upfront".
- When the author picks something other than your default, the workbench writes a rework brief in `briefs/`. Read it and redo only the parts it lists.

## Vanilla first (rule R9)

Every mod design stays inside vanilla Starfield. Use vanilla assets, or generate assets in the vanilla style. Take cues from existing vanilla styling and mechanics.

- Before you propose a design, find the closest vanilla example: a menu, an asset, a mechanic.
- Show that vanilla example on the whiteboard (a screenshot or an extracted preview). Name it in the board body: `Vanilla basis: <what it is>`.
- Build drafts from vanilla assets. If you need a new asset, describe how it matches the vanilla style.
- If a design needs something outside vanilla, do not choose it. Ask a question. Make the vanilla option the default.

## Where boards live

In each mod repo, listed in `workbench.toml`:

```
boards/open/<board id>/board.md      the board
boards/open/<board id>/<item files>  images, SWF, HTML, text
boards/open/<board id>/answers.json  written by the workbench, never by you
boards/done/<board id>/              closed boards
```

A board id is a short lowercase name with hyphens, for example `terminal-first-panel`.

## board.md format

A Markdown file. Front matter first, then a short body.

```markdown
---
title: First panel of the settlement terminal
raised_by: research
created: 2026-11-07T14:30
tags: [screen]
items:
  - file: current-menu.png
    caption: The menu in game today
  - file: draft-a.png
    caption: Layout option 1
  - file: draft-b.png
    caption: Layout option 2
  - file: usage.html
    caption: How often each stat is used
questions:
  - id: layout
    type: choice
    prompt: Which layout for the first panel?
    options:
      - {id: tabs, label: Tabs, item: draft-a.png}
      - {id: list, label: Single list, item: draft-b.png}
    default: tabs
    blocking: true
    affects: [ui/terminal_data.json, icons for the tab bar]
  - id: pacing
    type: yes
    prompt: Should building feel slow and careful?
    suggestion: Yes, with a short build time that you can skip.
  - id: dislikes
    type: text
    prompt: What would you hate to see in this menu?
---
Short context for the author. Two or three sentences.
```

### Fields

- `title`, `raised_by` (your workspace name, or `chat-<name>` in the app chat), `created`, `tags`: free text. The workbench shows any tag.
- `items`: files in the board folder. Each item needs a `caption`. The whiteboard is one large view that shows one item at a time. The captions become buttons that switch between items. Do not try to put several things side by side. To compare options, make one image that shows them together, or use several items. The workbench picks a viewer by file type. Images: png, jpg, webp, gif. HTML and SVG: shown in a sandbox with no scripts and no network. Text: prefer styled HTML (author, 2026-11-08). Copy `docs/board-html-template.html`: one self-contained file, inline CSS only, images only as `data:` URIs (the sandbox blocks scripts, network, external CSS and fonts). Plain `.md` and `.txt` still show, but only as a fallback. SWF: do not list a raw SWF, it draws blank (render a PNG, see "Showing a menu SWF on a board"). Item paths must stay inside the board folder.
- `questions`: each has `id` (unique in the board), `type`, `prompt`.
  - `choice`: 2 or 3 `options` and a `default` that is an option id. An option may name an `item` to highlight.
  - `yes`: one `suggestion`. The author answers yes or writes a different answer.
  - `text`: an open question. Use it for game play: what the author wants and does not want.
  - Every question has a comment field for the author. You do not declare it.
  - `blocking: true` means work that depends on it must stop. The author gets a toast. Use it rarely.
  - `affects`: the files or tasks that change if the author picks a non-default answer. The rework brief lists them.

## What goes on the whiteboard

The whiteboard is for illustration, not for questions. Put these on it: a game screenshot, a UI snapshot, a suggested rendering, an inspiration image, a data visualization, a diagram. For a data visualization, write an HTML or SVG file with inline CSS, no scripts and no network. A board with no items is fine.

Render PNGs (a mesh or object on a plain background) must be square or 16:9, at least 768 px on the short side, with one flat background color, the subject centered, and at least 5% margin on every side. `python -m workbench check` rejects a subject that is off-center by more than 4% or closer than 2% to an edge. The viewer fits every image whole (letterboxed, never cropped). Look at the board in the whiteboard, not only at the file, before you hand it over.

Game screenshots come from the orchestrator that tests the game (see below). Do not invent screenshots.

> - **Whiteboard text pages use the clay base style (hard rule, author, 2026-11-08).** Any whiteboard page that is not a screenshot of something real (text, tables, diagrams as HTML) must be built from `mod-workbench/docs/board-html-template.html`: clay cards, tokens, the style marker. Plain text on white is a defect. Calm colors only: cream page and cards, palette hues only as light tints or thin edges, never solid saturated fills. `python -m workbench check` rejects an HTML item without the marker. Every new workbench element or feature is styled from `web/tokens.css` and `web/clay.css`.

## Reading the answers

`answers.json` appears next to `board.md` after the author answers:

```json
{"answers": [{"question_id": "layout", "picked": "list", "text": null, "comment": "...", "answered_at": "..."}]}
```

A question with no entry has no answer yet. Continue on its default. Read the `comment` fields. They carry the author's feedback.

## Check before you finish

Run `python -m workbench check <board folder>`. It prints each problem. Fix them all. An invalid board shows as an error row and the author cannot answer it.

## Author notes on a board

The author can leave a note on a board item. The workbench writes it to `notes/<board id>-<n>.md` and types a `[workbench] event=note ...` line into your pane. Handle every note, and record the outcome **on the board itself**:

1. Read the note. Act on it: refine the text, drop the check, or answer the question.
2. Update the board so it shows the new status. Do not delete what the author sees.
   - A check or item the author says is done or not needed: remove its entry from `questions:` and add one entry to the `resolved:` list in the front matter: `{id, prompt, note, date}`. Keep the original prompt wording. Use `note: Confirmed by the author. No action needed.` The workbench shows it in the questions panel with a "Confirmed <date>" tag.
   - A change the author asks for: apply it, then add `Updated, <date>: <one line of what changed>` to the item.
   - If every question and check on the board is resolved, say so in the board body and tell the author. Do not close the board yourself; the author closes it.
3. Run `python -m workbench check <board folder>`.
4. Record the same fact in the repo's tracking file in the same edit.
5. Answer in one short line in chat or `messages/replies/`. The board is the record, not the chat.

## Status

Write your status in `status/<workspace>.toml` (for example `status/build.toml`). One file per workspace so two orchestrators never overwrite each other. Use any keys. The workbench shows each key as a column. Worker tables go under `[workers.<name>]`.

## Game tests

Rule R6: only the orchestrator starts or tests the game, on a fresh copy of the frozen baseline save. See `docs/game-testing.md`. Workers never start the game. Workers write a test spec (`tests/<id>.yaml`) and a line in the status file under `test_requests`.

Provisional: the build workspace runs game tests. The research workspace writes test specs and asks the build workspace. The author did not approve this yet.

## Add a new mod

See `docs/new-mod.md`. In short: `python -m workbench init <repo> --name <Name>`.

## You run in the app chat (no pane)

An agent that runs in the workbench app chat has no wmux pane. Its system prompt says so and gives the chat name.

- Set `raised_by: chat-<name>` on every board you raise. `<name>` is your chat name, for example `chat-main` or `chat-CityBuilder`.
- When the author answers, closes or reopens the board, or pins a note, the workbench sends you a chat message that starts with `[workbench board]`. If you are in a turn, the message waits until the turn ends.
- Act on the message and answer in the chat. Do not write a reply file. Do not register a pane.
- `python -m workbench check` accepts `chat-<name>` without a status file.

An agent in a terminal pane uses the next section.

## Register your pane (so the workbench can tell you things)

The workbench types a one-line `[workbench] ...` message into your wmux pane when the author closes or reopens a board you raised. It finds your pane in `status/<workspace>.toml` in your repo. The file name is the workspace name and must equal the `raised_by` value of your boards: `research.toml` (research), `citybuilder.toml` (CityBuilder build), `logistics.toml` (Logistics build). The main orchestrator raises boards with `raised_by: workbench` (file `status/workspaces/workbench.toml`). A `raised_by` with no matching file means the agent is never told, and the author sees "no pane is registered". Create the file if it does not exist. Add this line once per session (the pane id is in `$env:WMUX_SURFACE_ID`):

```
wmux_surface = "surf-..."
```

When you see `[workbench] ... closed this board`, read `boards/done/<id>/answers.json` and act on it. Do not ask the author to repeat anything.

## Messages and replies

The author sends free text from the message box. It lands in `messages/<id>.md` in your repo. Handle it, then write your answer to `messages/replies/<id>.md` (plain text, short) and move the message to `messages/done/`. The author sees your reply in the message box.

When you send a message to another pane, write file paths with forward slashes (`E:/repos/mods/...`). A shell or JSON string reads a backslash followed by the letter r (as in the folder name repos) as a carriage return, and the receiver gets a broken path.
` in `E:
epos` into a carriage return, and the receiver reads a broken path.

## Showing a menu SWF on a board

Do not put a raw SWF on a board. It draws blank. Render a PNG with the owning repo's preview script (Logistics: `pwsh -File build/preview/preview.ps1 -View <name>`, ~15 s per view). Copy the PNG into the board folder and list it under `items`.

## Stopping (enforced by a Stop hook, 2026-11-08)

An orchestrator may end a turn only when its repo has an open board, or its status file says `phase = "finished"` and `summary = "<one line>"`. A board tagged `permanent` does not satisfy this gate, so the hook still blocks when your only open boards are permanent ones. Otherwise the hook blocks the stop once. The hook also saves your last chat message as `messages/replies/<id>.md` for each unhandled author message and moves the message to `messages/done/`. Write the reply file yourself when you want exact text.

## SDK tools
Read `docs/sdk-chat/sdk-surfaces.md`, `opencode-surfaces.md` and `sdk-highlights.md` before you build a new workbench tool. They list every SDK connection point. Regenerate with `scripts/sdk_surfaces.py` after an update.
