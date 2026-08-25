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
python -m etl.pipelines.gen5_trainers blackwhite
python -m etl.pipelines.gen5_trainers blackwhite --apply
python -m etl.pipelines.gen5_event_bosses black2white2 --apply
```

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

Ported: Gen 5 trainers and event bosses (Black/White, Black 2/White 2). The
old `load_blackwhite_build6_*.py` and `load_black2white2_build6_*.py` scripts
now forward here so existing commands keep working. `derive_location_areas`
is new and covers every version group whose trainers carry map references
(1, 2, 3, 4, 8, 9, 10 — Gen 3 and Gen 5 previews do not record one).

Not yet ported: the preview *builders* (ROM and decomp extraction) and the
Gen 1-4 loaders and updaters. They still carry their own absolute paths. Port
opportunistically — a pipeline that needs to be re-run is a good reason.
