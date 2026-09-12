# ADR-0005: ROM Hacks As Their Own Version Groups

- Status: Accepted
- Scope: ROM hack support; first instance Blaze Black / Volt White

## Decision

A ROM hack is a first-class `games` row with its own `game_id` and its own
`version_group_id`, both allocated from the reserved 1000+ range (Blaze
Black = game 1001, Volt White = 1002, shared version group 1001). The link
to the vanilla game lives in `games.base_game_id`, with `games.is_rom_hack`
for UI grouping. Because `version_group_id` is a hard equality in every
trainer, boss, script, and area query, a hack's data is fully isolated from
its base with no read-path changes.

A hack's version group is seeded by cloning the base
(`etl/pipelines/clone_version_group.py`): the structural clone copies the
route script and areas; `--full` also produces a playable copy. Rows
exclusive to an unmapped base game are dropped, never turned shared. New
games land `valid_game='hidden'` until launch. Hack content then loads over
the clone from the hack's own ETL at its own load build.

The permissive nullable-`game_id` overlay on `trainer_pool`/`event_bosses`
remains what it always was — version exclusives *within* a version group
(Black vs White, Blaze Black vs Volt White) — and is never used to layer a
hack onto its base.

Frontend consequences are confined to selection and assets: NewRun shows a
ROM Hacks section ("Hack of <base>" badge), logos and trainer sprites fall
back hack → base (sprites resolve by `games.generation`), and
`event_bosses.is_level_cap` / `battle_type` replaced the hardcoded
event-type string list.

## Evidence

- Migration: `Backend/migrations/20260829_game_variants.sql`
- Seeding: `Backend/etl/pipelines/clone_version_group.py`
- Rails proof: a `--full` clone of Black produced an 85-row script
  machine-verified identical to vanilla (WP7, commit 82ef5ae)
- Blaze Black instance: `Backend/etl/pipelines/blazeblack/`, manifest
  `Backend/etl/manifests/blazeblack.json` (WP8, commit 118441e)
