# Lockley ETL

Shared machinery for the pipelines that populate trainers, parties, event
bosses, and encounters.

Before this package each generation was its own dialect: 22 copies of a
hardcoded `psql.exe` path, 19 copies of the `.env` reader, 21 inlined
`subprocess.run` calls, and the `trainer_pool` / `trainer_pokemon` field lists
spelled out six times each. Nothing ran on a machine that wasn't this one.

## Layout

| Module | Responsibility |
|---|---|
| `config.py` | Every path, resolved from environment variables. No absolute paths anywhere else. |
| `db.py` | psql invocation: `run_sql`, `query_rows`, `query_scalar`. Always `ON_ERROR_STOP=1`. |
| `preview.py` | Preview CSV read/write plus the reusable validators (`expect_row_count`, `expect_unique`, ...). |
| `schemas.py` | The staged column lists, as one definition each. |
| `normalize.py` | Constant/name normalization shared across source formats. |
| `loader.py` | `GuardedLoad`: stage → `\copy` → guards → insert → metrics → commit/rollback. |
| `manifests.py` + `manifests/*.json` | Per-data-set configuration: ids, source, expected counts. |
| `pipelines/` | One module per data set, driven by a manifest. |

## Configuration

Nothing is hardcoded. Set what a given pipeline needs:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string. Falls back to `Backend/.env`. |
| `PSQL_PATH` | psql executable. Falls back to the default install, then `PATH`. |
| `LOCKLEY_ROMS_DIR` | Root holding retail ROM files (ROM-extraction pipelines). |
| `LOCKLEY_DECOMPS_DIR` | Root holding decomp checkouts. |
| `LOCKLEY_ETL_SOURCE_DIR` | Root holding other source documents (e.g. ROM hack docs). |
| `LOCKLEY_PREVIEW_DIR` | Where preview CSVs live. Defaults to `Backend/`. |

## Running a loader

Dry run is always the default — nothing commits without `--apply`:

```bash
python -m etl.pipelines.load_trainers redblue
python -m etl.pipelines.load_trainers crystal --apply
python -m etl.pipelines.load_trainers blackwhite --apply
python -m etl.pipelines.gen5_event_bosses black2white2 --apply
```

`load_trainers` works for every manifest — the stage adapts to the columns
the preview actually carries. `gen5_trainers` remains as an alias.

Trainers must load before event bosses: bosses resolve their trainer by
`encounter_name` against the same version group and build.

Some pipelines derive from data already in the database rather than from a
preview. `derive_location_areas` reads the map reference in each trainer's
`details` blob and turns it into a `location_areas` row:

```bash
python -m etl.pipelines.derive_location_areas --apply
python -m etl.pipelines.derive_location_areas --version-group-id 1
```

It only fills empty `area_id`s, so curated assignments survive a re-run;
pass `--reassign` to overwrite them.

The variant model (WP7) seeds a ROM hack's version group from its base game:

```bash
python -m etl.pipelines.clone_version_group --base-vg 11 --new-vg 1001 \
    --game "1001:17:Blaze Black" --game "1002:18:Volt White" --apply
```

Hack ids live in the reserved 1000+ range. The structural clone copies the
route script and areas; `--full` also clones trainers, parties, bosses, and
encounters into a playable copy (game-exclusive rows of unmapped base games
are dropped, never turned shared). New games rows land hidden until launch
(`--valid-game valid` to expose them).

Blaze Black (WP8) is the first ROM hack, parsed from Drayano's documentation
rather than a ROM. Convert the RTF docs to UTF-8 text (PowerShell:
`System.Windows.Forms.RichTextBox` reads the RTF, write `.Text` out as
UTF-8), put them in `LOCKLEY_ETL_SOURCE_DIR/blazeblack/`, then:

```bash
python -m etl.pipelines.blazeblack.build_previews   # docs -> preview CSVs
python -m etl.pipelines.load_trainers blazeblack --apply
python -m etl.pipelines.gen5_event_bosses blazeblack --apply
python -m etl.pipelines.load_encounters blazeblack --apply
```

The preview build resolves every species, move, ability, and location
against the live database and matches every boss team to the vanilla BW
skeleton (61/61) -- it exits non-zero on unresolved names, so a clean run
means the data is load-ready. Rival teams expand into per-starter variants
using the vanilla starter mapping.

The species/learnset override layer ("Pokemon Changes" + "Level Up Move
Changes") loads via `load_species_overrides`: Regular-mode abilities for
every species, changed stat spreads and typings, materialized level-up
learnsets (vanilla vg-11 copy plus the doc's +/-/= deltas, including
family-grouped and full-restructure blocks), and rebalanced move data --
all keyed at vg 1001. Read paths prefer exact version-group rows and fall
back to the base game. Two learnset entries reference Drayano's custom
move "Wood Horn", which exists nowhere in our move data and is skipped
with a note.

Placement curation (WP5) adds two more:

```bash
python -m etl.pipelines.build_placement_suggestions --apply   # rebuild advisory suggestions
python -m etl.pipelines.apply_curated_placements --version-group-id 11 --apply
```

`build_placement_suggestions` mines candidate notes and map references from
`trainer_pool.details`, the Gen 5 previews' `map_reference_details.csv`, and
the B2W2 Serebii cross-check into `trainer_placement_suggestions` for the
`/admin/placement` surface. Suggestions are advisory; humans accept them.
`apply_curated_placements` re-applies accepted decisions
(`curated_trainer_placements`) outside a loader run; the Gen 5 loaders embed
the same statement, so re-extraction never loses curation.

## Adding a data set

Add a manifest to `manifests/` and reuse an existing pipeline if the shape
matches. A ROM hack is a manifest with `is_rom_hack: true` and a `base`
pointing at the manifest it derives from — not a new script.

## Design notes

**Guards are the point.** A load refuses to run rather than write something
unexpected: wrong version group or build, a row count that disagrees with the
manifest, data already present, or a reference that doesn't resolve. A tripped
guard exits non-zero and prints what the database said; that is a normal
outcome, not a crash.

**Loads are portable.** Event bosses bind to trainers by `encounter_name`, not
by the database-assigned `trainer_id` the old previews baked in — those ids
were only valid in the one database the trainers happened to be inserted into,
which made a fresh-database load impossible. This matters for cloning a
version group when seeding a ROM hack.

**Party rows carry identity.** `trainer_pokemon` rows are linked to
`trainer_pool` by `trainer_id` and numbered by `slot` inside the load
transaction, and the load aborts if any row fails to link.

**Badges are not a loader concern.** `event_bosses.badge_id` is assigned by
migrations (see `migrations/20260825_unova_badges.sql`), so a preview does not
have to know badge numbering.

## Migration status

Ported: trainer loads for every version group with a preview — Gens 1, 2, 4
(builds 4-5, previously loader-less) and Gen 5 (build 6), all through
`load_trainers` with a manifest each, verified loading into a fresh database.
Gen 5 event bosses load through `gen5_event_bosses`. The old
`load_*_build*.py` forwarding shims were retired to `archive/Backend/`; use
the `etl.pipelines` commands above.
`derive_location_areas` covers every version group whose trainers
carry map references (1, 2, 3, 4, 8, 9, 10 — Gen 3 and Gen 5 previews do not
record one).

Not ported: the preview *builders* (ROM and decomp extraction), the Gen 1-4
event-boss updaters, and Gen 3 (version groups 5-7), which has no previews at
all — its data predates the preview discipline and re-extraction is the
outstanding stretch item. Those legacy one-off scripts (and the pre-ETL
sqlite-era loaders) live in `archive/Backend/`; they are kept for reference
and are not importable from there without moving them back.
