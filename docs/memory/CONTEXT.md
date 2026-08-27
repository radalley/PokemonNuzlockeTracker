# Lockley Current Context

Lockley is a multi-game Pokemon Nuzlocke tracker. The React/Vite frontend lives
in `Frontend/`; the Python API and Postgres data access live in `Backend/`.
Supabase provides authentication and production Postgres. Guest runs use local
browser storage.

Current architecture areas established in this design thread:

- Contact submissions are internal `contact_reports`, not direct user email.
  Admins manage reports and statistics at `/admin/reports`.
- The main menu can continue the authenticated user's most recently opened run.
  `runs.last_opened_at` and `runs.last_opened_attempt_number` track this state.
- Badge awards are event-driven. `event_bosses.badge_id` identifies the award,
  and wins create normalized `attempt_badges` and `pokemon_badges` rows.
- `.agent-memory/` is the local cross-agent knowledge base. Codex and Claude
  hooks capture conversations and inject bounded, relevant recall.
- 2026-08-24 overhaul plan: `docs/overhaul-plan-2026-08.md` is the canonical
  three-day implementation plan (WP0-WP9) for trainer identity hardening,
  full-fleet placement, ROM hack rails, and the Blaze Black launch. Follow its
  ground rules: guarded SQL migrations only, single migration owner, additive
  schema changes, guest-mode parity, verify counts against production.
- Overhaul progress: WP0 done (commit 9d6bf99 — Backend/schema.sql baseline,
  Backend/migrations/apply.py runner, both proven idempotent against the dev
  DB). WP1 done (commit 5cf1fe0 — trainer_identity migration applied to dev,
  id-keyed party endpoint, loader links trainer_id, TrainerCard uses it; 40
  backend + 22 frontend tests green, live smoke verified). Dev-DB backups:
  C:\Users\radal\Lockley-backups\2026-08-24. The migration has NOT been
  applied to production Supabase yet — run Backend/migrations/apply.py with a
  production DATABASE_URL before deploying this code. WP2 done (commit
  ba61f60 — guest trainer lists send game context, Unova badges 33-42 via
  migration 20260825_unova_badges.sql, debug endpoint requires admin,
  create_run takes explicit game_id; 47 backend + 25 frontend tests green,
  live smoke verified). Pool fixes (commit ae590c5 — lazy-init race + burst
  exhaustion, found by driving the app locally). WP3 done (commit 45fd649 —
  Backend/etl/ package: config/db/preview/schemas/normalize/loader/manifests
  /pipelines; gen5 trainers and event bosses are manifest-driven; old build-6
  loaders are forwarders; verified end-to-end on a throwaway database).
  WP4 done (commit 2c9c77e — `location_areas` table below `canon_locations`,
  nullable `trainer_pool.area_id`, derived from ETL map references by
  `etl/pipelines/derive_location_areas.py`; 406 areas / 77 gyms across
  version groups 1,2,3,4,8,9,10 and 1,617 of 4,650 placed trainers grouped.
  Gen 3 and Gen 5 previews record no map reference, so they derive nothing).
  WP5 done (commit 65d458c — curated_trainer_placements +
  trainer_placement_suggestions, /admin/placement page, admin endpoints,
  suggestion builder pipeline; 140 trainers placed on dev via the endpoints;
  loaders re-apply curation, proven on a scratch reload). Known WP6 input:
  52 unplaced BW trainers stand in places missing from canon_locations
  entirely (Nimbasa City, Opelucid City, Mistralton City, Challenger's Cave,
  Shopping Mall) — adding trainers-only script locations is a script-content
  decision — RESOLVED in WP6. WP6 done (commit 1cf5830 — generic
  load_trainers pipeline + manifests for all nine preview data sets, verified
  loading into a fresh scratch DB; rematch/event opt-in behind a LocationRow
  toggle; BW script locations 492-495 added for Nimbasa/Mistralton/Opelucid/
  Challenger's Cave and all 52 blocked BW trainers placed, 4 onto Route 9 as
  Shopping Mall Nine). Gen 3 (vgs 5-7) remains the no-previews stretch item.
  Day 2 of the overhaul plan is complete. WP7 done (commit 82ef5ae — variant
  model: games.base_game_id/is_rom_hack, event_bosses.battle_type/
  is_level_cap (193 cap rows backfilled, fixes Gen 5 caps), reserved 1000+
  id range, clone_version_group pipeline with --full playable copies and
  unmapped-exclusive dropping, NewRun ROM Hacks section with base-logo
  fallback, sprite folders keyed on games.generation, get_script stable
  ordering. Rails smoke test: a full clone of Black played IDENTICALLY —
  85-row script matched on names/counts/badges/caps — then was removed;
  vg 1001 and game ids 1001/1002 are free for Blaze Black/Volt White).
  WP8 done (commit 118441e — Blaze Black loaded as vg 1001, games 1001/1002,
  build 7, valid_game='hidden'. Doc parsers in etl/pipelines/blazeblack/
  read LOCKLEY_ETL_SOURCE_DIR/blazeblack/*.txt (C:\Users\radal\
  Lockley-etl-sources\blazeblack, converted from the OneDrive RTFs).
  355 trainers / 1,223 party rows (Regular+Clean abilities, doc-exact
  movesets) / 61 bosses matched 61/61 to the vanilla skeleton / 2,036
  encounter rows. Five more vanilla BW script locations added (migration
  20260830: Nuvema, Accumula, Icirrus City, Moor of Icirrus, Tubeline
  Bridge). backend fix: _normalize_move_constant handles display names).
  WP9 done (commit edc604e) — THE OVERHAUL PLAN (WP0-WP9) IS COMPLETE.
  Blaze Black is LIVE ON LOCAL DEV ONLY (games 1001/1002 valid locally);
  production is untouched by explicit user decision. Guest and
  authenticated smokes passed (Trio Badge awarded exactly once, replay
  safe). A 14-agent adversarial review of the full diff confirmed and WP9
  fixed three defects: hack version groups now resolve movesets against
  their base game's vg (_moveset_version_group_for), get_db returns failed
  connections via putconn(close=True), and load_trainers' already-loaded
  guard is version-group-wide. Production launch = the ordered runbook in
  docs/blazeblack-launch-runbook.md (backup -> migrations BEFORE code
  deploy -> deploy -> hidden loads -> verify -> flip); 11 commits sit
  unpushed on local uat — confirm which branch Render deploys from before
  the first push. Species/learnset override layer done 2026-08-25 (commit
  55d7a20 — migration 20260831 adds version_group_id to species_abilities/
  stats/types; parsers for "Pokemon Changes" + "Level Up Move Changes";
  overrides loaded at vg 1001: 649 abilities / 138 stats / 18 types /
  8,815 learnset rows / 46 rebalanced moves; resolvers prefer exact vg then
  base-game fallback; verified live and isolated from vanilla; adversarial
  gate review was still running at commit time — check for follow-up fix
  commits). Remaining deferred: guest script assembly consolidation, Gen 3
  re-extraction; custom move "Wood Horn" unrepresentable (2 learnset
  entries skipped).
- 2026-08-27: observed-moves overlay live (commit 3c0b48a).
  `curated_trainer_moves` records opponents' moves the admin sees in
  battle, keyed (vg, encounter_name, slot, move) with a species guard;
  never touched by loaders. Attaches to id-keyed party fetches as
  `observed_moves`; TrainerCard shows green "seen" pills for everyone,
  admin-only add box (datalist over /api/moves/search) + remove.
  Admin API: POST/DELETE /api/admin/trainer-moves. Portable via
  `sync_curated_moves export|load` (CSV MIRRORS the vg: load deletes
  rows the CSV dropped; empty CSV refused). The chat has pivoted to
  play-driven refinement during the user's Blaze Black run; the
  proposal backlog (sheets import, dead-run summary, timeline, career,
  encounter-controls rework, ability-on-catch, mobile) was reviewed
  2026-08-27 with sequencing in the conversation.
- 2026-08-25: BW (vg 11) full-fleet placement DONE — 615 trainers fully
  accounted (524 placed / 61 boss-linked / 30 curated-excluded, 0 gaps),
  researched by a 22-agent verify workflow and curated via the new
  status/flags columns on `curated_trainer_placements`. Portable curation
  CSV: `Backend/etl/curation_data/vg11.csv` (`sync_curated_placements
  export|load`). Venue script rows added (Royal Unova 501, Big Stadium &
  Small Court 502, Black City 503, Pokémon League 226); misspelled canon
  Icirrus/Moor duplicates consolidated onto 498/499. The Trainers filter
  now surfaces special-only venues via `special_trainer_count` (+N★).
  B2W2/DP/Pt placement remains open.
- 2026-08-24 review (context for the above): full trainer coverage is a
  placement problem, not extraction — most trainers exist in `trainer_pool`
  without a `canonical_location_id`, and only script locations can surface
  trainers. Proposed direction: harden `trainer_pokemon` to join by
  `trainer_id`, add a `location_areas` placement level under canonical
  locations, and model ROM hacks (first target: Blaze Black) as their own
  `game_id` + own `version_group_id` seeded copy-then-override from the base
  game, with `games.base_game_id` and `is_rom_hack` metadata. Blaze Black 3.1
  documentation (OneDrive, RTF) converts cleanly to text and covers trainers,
  bosses with movesets, and wild encounters.

Local dev startup (added 2026-08-25): `start.ps1` at the repo root launches
both servers in one console (`.\start.ps1`, or `start.cmd` to bypass the
execution policy; `-BackendOnly` / `-FrontendOnly` to run one). It resolves
the backend interpreter itself, guards ports 5000/5174, and kills the whole
process tree on exit. Gotcha it encodes: `Backend` contains two venvs and only
`Backend\venv` is provisioned — `Backend\.venv` and the root `.venv` are
missing flask/psycopg2, which is why bare `python api.py` fails with
`ModuleNotFoundError: No module named 'jwt'`.

Verify all memory against the current worktree and database before changing
behavior. Local backend or database availability has previously looked like an
authentication or empty-data regression from the frontend.
