# Blaze Black Production Launch Runbook

Blaze Black / Volt White are live on the local dev database and fully
smoke-tested (guest and authenticated). Production has none of it yet —
neither the overhaul's schema migrations nor any hack data. This is the
ordered checklist for taking production live, written to be executed in one
sitting. Nothing here runs automatically; every step is a deliberate manual
action.

**Ordering matters in exactly one place:** the deployed code references
columns the migrations create (`trainer_pokemon.trainer_id`,
`location_areas`, `event_bosses.is_level_cap`, `games.base_game_id`).
Migrations must reach Supabase BEFORE the code deploys, or script and
trainer endpoints will 500. The reverse order is invisible to users.

## 0. Preconditions

- [ ] Confirm which branch Render actually deploys from (dashboard — there
      is no render.yaml). If it deploys from `uat`, do NOT push until step 2
      is done.
- [ ] Back up production: `pg_dump` schema plus data dumps of
      `trainer_pool`, `trainer_pokemon`, `event_bosses`, `event_locations`,
      `games`, `badges`, `canon_locations`, `location_areas` to a dated
      folder.

## 1. Point the tooling at production

All commands run from `Backend/` with the production connection string in
the environment for that shell only:

```bash
set DATABASE_URL=<production Supabase URL>
```

(Or `$env:DATABASE_URL = "..."` in PowerShell. `Backend/.env` stays
pointed at local dev.)

## 2. Schema migrations (idempotent, additive-only)

```bash
python migrations/apply.py
```

Expect eight newly applied names, `run_last_opened_backfill_v1` through
`bw_script_locations_v2` (whichever were not already applied). A second run
must report nothing new.

- [ ] Verify: `trainer_identity_v1` notice reported a backfill count and
      `select count(*) from trainer_pokemon where trainer_id is null` is
      small (locally: 35 legacy Gen 3 orphans).

## 3. Deploy the code

Now push/merge so Render deploys. CI (tests) runs on push to `main`/`uat`.

- [ ] Verify the deployed app still serves a vanilla run normally
      (script, trainer panels, a party fetch).

## 4. Hack structure and data (still invisible to users)

```bash
python -m etl.pipelines.clone_version_group --base-vg 11 --new-vg 1001 --game "1001:17:Blaze Black" --game "1002:18:Volt White" --apply
set LOCKLEY_ETL_SOURCE_DIR=C:\Users\radal\Lockley-etl-sources
python -m etl.pipelines.blazeblack.build_previews
python -m etl.pipelines.load_trainers blazeblack --apply
python -m etl.pipelines.gen5_event_bosses blazeblack --apply
python -m etl.pipelines.load_encounters blazeblack --apply
python -m etl.pipelines.fill_encounter_gaps blazeblack --apply
python -m etl.pipelines.load_species_overrides blazeblack --apply
```

`fill_encounter_gaps` inherits base-game pools for locations the docs
omit (the Starter pool); run it after `load_encounters` or the
already-loaded guard sees its rows as a partial load.

The preview build must end with `base skeleton matched 61/61` and exactly
four notes (the N's Castle story capture skipped twice -- no canonical
location, matching vanilla -- and the custom move Wood Horn twice) before
the loads. The games land `valid_game='hidden'`: nothing
user-visible has changed yet.

- [ ] Verify hidden: `/api/games` does not list Blaze Black; counts match
      local (355 trainers / 1,223 party rows, 0 unlinked / 61 bosses /
      2,312 encounter rows for games 1001+1002, incl. 6 inherited Starter
      rows / overrides at vg 1001: 649 abilities, 138 stats, 18 types,
      8,794 learnset rows, 46 moves).

## 5. Flip

```sql
update games set valid_game = 'valid' where game_id in (1001, 1002);
```

- [ ] Verify live: ROM Hacks section appears in New Run; create a test run;
      Striaton Gym shows Level Cap 14 and awards the Trio Badge exactly
      once; delete the test run.

## Rollback

Any step can stop safely. To unlaunch: flip `valid_game='hidden'` back
(runs already created on 1001/1002 keep working). To remove the data
entirely, delete in FK order: encounter_pool (games 1001/1002),
event_bosses, trainer_pokemon, trainer_pool, location_areas,
event_locations (vg 1001), then the games rows. Migrations are additive and
never need reverting for this feature.
