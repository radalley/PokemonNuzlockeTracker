# Archive

Material no longer in use by the running application, moved here 2026-08-27
after a reference audit confirmed nothing live (api.py, backend.py, etl/,
tests/, migrations/, Frontend, scripts/, start.ps1, Procfile, CI, operational
docs) imports or invokes any of it. Kept for reference; deleting this folder
would lose nothing the app needs.

## What lives here

- `Backend/load*.py`, `Backend/Load*.py`, `Backend/MergeLocations.py` — the
  pre-ETL sqlite-era seeding scripts (PokeAPI pulls into `identifier.sqlite`,
  then `loadPG.py` into Postgres). Superseded by `Backend/etl/`.
- `Backend/build_*_preview.py` — the original preview builders (ROM/decomp
  extraction). Their *outputs* — the `Backend/<game>_build*_preview/` folders —
  are still the ETL's staging inputs and stay in `Backend/`.
- `Backend/load_*_build*.py` — deprecated forwarding shims into
  `etl.pipelines`; use `python -m etl.pipelines.<name>` directly. They import
  from `etl`, so they no longer run from inside the archive.
- `Backend/update_*.py` — one-off data fixups (trainer pics, items, event
  bosses, locations) whose changes are long since in the database. Note the
  Gen 1-4 event-boss updaters were never ported to the ETL, so if that data
  ever needs re-deriving these are the starting point.
- `Backend/download_*` / `freeze_*` / `set_gen4_apng_play_once.py` — sprite
  acquisition/processing one-offs; the sprites live in
  `Frontend/public/sprites/`.
- `Backend/guiTest.py`, `pyGuiMain.py`, `main.py`, `temp.py`,
  `testPokemon.py`, `diag_loc.py` — pre-web CLI/GUI prototypes and scratch
  diagnostics.
- `Backend/*_bulk_raw_*`, `poke_db`, `poke_db.sqlite`, `identifier.db`,
  `identifier.sqlite` (also one at archive root, ~97MB), `seed_cache/` — raw
  inputs and sqlite databases the legacy scripts read/wrote. Postgres is the
  only live datastore.
- `Backend/crystal_build4_preview_regression_tmp/` — an orphaned scratch copy
  of the crystal preview; the live one remains `Backend/crystal_build4_preview/`.
- `staged-files.txt` — stray scratch listing from an old cleanup.

## Warnings

- `Backend/loadPG.py` contains hard-coded legacy Postgres credentials. They
  should be treated as burned and rotated; do not reuse them.
- Nothing here is on the Python path. Anything revived should be moved back
  (or better, ported into `Backend/etl/`).
