# Add a mod to the workbench

Do this for CityBuilder or any new mod repo.

1. Run from the mod-workbench folder:
   `.venv/Scripts/python -m workbench init <path to the mod repo> --name <Mod name>`
2. The command writes `workbench.toml` and creates `boards/open`, `boards/done`, `status` and `notes`. It never overwrites an existing file.
3. Add three lines to the repo's `CLAUDE.md` or `AGENTS.md`:
   ```
   ## Workbench
   Ask the author questions and show drafts on a workbench board. Use the `workbench-board` skill.
   Config: `workbench.toml`. Guide: `E:\repos\mods\mod-workbench\docs\orchestrator-guide.md`.
   ```
4. Start the workbench with `.venv/Scripts/python -m workbench serve`. The new mod appears in the rail. The server scans `E:\repos\mods` (set `WORKBENCH_ROOTS` to change it).

A mod that lives inside another repo (CityBuilder is inside StarfieldModResearch) needs its own folder with its own `workbench.toml`, or it shares the parent repo's boards. Ask the author which.
