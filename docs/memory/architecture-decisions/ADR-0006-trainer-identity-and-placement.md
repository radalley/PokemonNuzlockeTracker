# ADR-0006: Trainer Identity, Placement Areas, And Curation

- Status: Accepted
- Scope: Trainer data model and the full-fleet placement workflow

## Decision

**Identity.** `trainer_pokemon` rows link to `trainer_pool` by `trainer_id`
(with explicit `slot` ordering and `ability`/`ability_clean`/`nature`
columns); the party endpoint is id-keyed
(`GET /api/trainers/<trainer_id>/party`). The legacy encounter-name string
join remains only as a fallback for 35 unbackfillable Gen 3 rival orphans.

**Placement.** Canonical locations stay the run script's grain; a
`location_areas` level below them (gym, interior, cave floor) carries where
trainers actually stand, derived mechanically from the ETL's map references
where they exist (`derive_location_areas`). The trainer panel groups by
area; rematch and event trainers are opt-in extras, never counted in
progress.

**Curation.** Human placement decisions are durable data:
`curated_trainer_placements` is keyed by the stable ETL identity
(version group + encounter name) and re-applied inside every trainer
loader's transaction, so re-extraction never loses curation. Machine
suggestions (`trainer_placement_suggestions`, rebuilt by
`build_placement_suggestions` from extractor notes, map references, and the
Serebii cross-check) are advisory only; `/admin/placement` is where a human
accepts them.

**Curation scope (2026-08-25).** Curated rows also carry `status`
('placed' | 'excluded' — the latter resolves unused ROM data such as
nameless Patrat-L10 placeholder trainers out of the gap metrics),
`is_rematch`/`is_event`/`game_id` (applied onto trainer_pool as
'1'/'0'/int, overriding the extractor), and a `note` with the evidence.
The portable form is a repo CSV under `Backend/etl/curation_data/`
(`sync_curated_placements export|load`), which is how curation reaches
production and scratch rebuilds. An unplaced trainer only counts as a gap
when it is neither excluded nor attached to an `event_bosses` row
(bosses display through the boss skeleton, never location panels).
Venue trainers (Big Stadium & Small Court, Royal Unova, Black City /
White Forest residents, League rematches) are flagged rematch/event so
they surface in panels — and in the Trainers filter via
`special_trainer_count` — without ever counting toward run progress.

## Evidence

- Migrations: `20260824_trainer_identity.sql`, `20260826_location_areas.sql`,
  `20260827_placement_curation.sql`
- Reload-survival proof: a curated decision survived a from-scratch Gen 5
  reload on a scratch database (WP5, commit 65d458c)
- Every preview data set (version groups 1-4, 8-11, 14, 1001) loads from
  scratch through `etl/pipelines/load_trainers.py` with all party rows
  linked and slotted (WP6, commit 1cf5830)
- Full BW (vg 11) coverage 2026-08-25: 615 trainers = 524 placed +
  61 boss-linked + 30 excluded, 0 actionable gaps. 236 researched by a
  22-agent workflow (12 researchers + per-location Bulbapedia/Serebii
  roster verifiers; 232/236 verified high-confidence, 4 hand-adjudicated).
  Misspelled canon duplicates (Iccirus City 248 / Moor of Icarus 250)
  consolidated onto 498/499 (`20260901_icirrus_consolidation.sql`); venue
  script rows added for Royal Unova 501, Big Stadium & Small Court 502,
  Black City 503, Pokemon League 226 (`20260903_bw_venue_locations.sql`).
