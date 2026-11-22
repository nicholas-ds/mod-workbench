# Game testing rules

Status: draft for approval. Date: 2026-11-07. Rule R6.

## 1. Who may test

- Only an orchestrator launches the game and runs tests. Each workspace tests its own work (author, 2026-11-08): research tests research items, the Logistics build workspace tests Logistics, the CityBuilder build workspace tests CityBuilder.
- One game runs at a time. Before you start it, check that `Get-Process Starfield` returns nothing. If the game runs, wait or ask on a board.
- Workers never launch the game. A worker that needs a test result writes a test request. The orchestrator runs it.
- The orchestrator never loads the author's main save.

## 2. The baseline save

- The platform repo holds one frozen baseline save, with a recorded SHA-256 hash.
- No tool writes to the baseline. Only the author replaces it, by an explicit action.
- Every test uses a fresh copy of the baseline. A script restores the copy into a test slot. The orchestrator does not copy files by hand.

## 2b. Save names (author decision, 2026-11-08)

- The baseline is named `WB-BASELINE`. It is a clean save in the Zamka outpost, with no probe or test mod state. Only the author makes or replaces it.
- A save an agent makes during a test is named `WB-TEST-<workspace>-<date>`, for example `WB-TEST-research-20261108`. No other prefix.
- The game writes autosaves during a test. The orchestrator lists them after the test.
- Cleanup deletes only `WB-TEST-*` files and the autosaves listed for that test. It never deletes `WB-BASELINE` or any other save.
- Old names (`rp1`, `Save9001_*`, `SLTEST*`) are retired. Do not create new saves with them.

## 2a. The test slot and the backup

- The test slot is the quicksave file. The restore script writes the baseline copy into it.
- The orchestrator quicksaves only after it loads the test slot. A quicksave is a checkpoint inside the test. It is never a step before the load.
- Before every test, the runner copies the main save folder to `backups/<date-time>/`. The runner keeps the last 5 backups. (Builder call on 5.)
- The runner never writes to a backup after it creates it.

### One script for backup and restore

- One script does steps 1 to 4 of section 5: `scripts/restore_test_slot.py`. One command runs it.
- The script checks the baseline hash, backs up the main save folder, writes the baseline copy into the test slot, and checks the result hash.
- The script exits with code 0 on success. It exits with a non-zero code and a one-line reason on any failure.
- The script takes no arguments for a normal run. Optional flag: `--dry-run` prints what it would do.
- The runner calls this script. The author can also run it by hand.
- The script must finish in a few seconds. It copies files and does nothing else.

## 3. Test spec

A test spec is a file in the mod repo (`tests/<id>.yaml`). It holds:
- `baseline`: the id of a baseline save. You must set this field.
- `goal`: one sentence.
- `steps`: a numbered list. Each step has an `action` and an `expect` (what must be seen).
- `evidence`: what to record for each step (screenshot, log pattern, console output).

The test runner refuses any spec that:
- has no `baseline` field,
- names any save other than a registered baseline,
- names a save slot that is not the test slot.

## 4. What the orchestrator may test

- Behavior that a test spec describes: a mod loads, a menu opens, a function returns a value, a screen shows the right data.
- Only mods that are in the mod repos under the workbench.
- Only on the test slot, one test at a time.

The orchestrator does not test:
- anything on the main save or in the main save folder,
- anything that a spec does not list (no free exploring),
- judgments of look or feel. These need the author (section 7).

## 5. How a test runs

1. Check that the baseline hash equals the recorded hash. If not, stop (section 7).
2. Copy the whole main save folder to a dated backup folder. Record the hash and modified time of the main save folder.
3. Run the restore script. It copies the baseline into the test slot.
4. Check that the test slot file hash equals the baseline hash.
5. Launch the game from the test runner. The runner loads the test slot with quickload. It never uses "continue".
6. Run each step. For each step, record the evidence the spec asks for.
7. Close the game.
8. Check that the main save folder hash and modified time did not change.
9. Write the report (section 6).

Logs to collect: the game log, the Papyrus log, the SFSE log, and the runner log. Save them with the report.

## 6. Pass and fail evidence

- A step passes only when recorded evidence shows its `expect` (a screenshot or a log line). A claim with no evidence is a fail with the reason "unverified".
- A test passes only when every step passes and step 8 passes.
- The report is a file in `exports/`. It holds: spec id, baseline hash, test slot hash, each step with result and evidence path, log paths, and the final result.
- The workbench shows the report. It shows no result without a report file.

## 7. When the orchestrator must stop and write a decision card

Stop the run, close the game, and write a card in each of these cases:
- A step fails or has no evidence.
- The game crashes or hangs.
- The baseline hash, the test slot hash, or the main save check fails. Do not repair it. Write a blocking card.
- The state is not what the spec expects, and the spec has no step for it.
- A step needs a choice that the spec does not give.
- The spec names a save that is not a baseline.
- The result depends on how something looks, feels or reads. This is a UI decision (rule R3).
- Two retries of the same test fail in a row.

A card from a failed test is `blocking: true`. It includes the report path.

## 8. Enforcement

These rules must not rely on good behavior alone.
- The test runner is the only program that launches the game. Worker environments do not have its path.
- The runner checks the spec (section 3) before the game opens.
- The runner checks the main save (steps 2 and 8).
- Builder call: the runner holds a lock file so that only one test runs at a time.

## 9. Not decided

- The save folder path and the quicksave file name. The builder reads them from the game on this machine.
- Whether the game loads the quicksave file with the restored copy as expected. The first runner task must test this.
- How the runner takes screenshots (game overlay or screen capture).
