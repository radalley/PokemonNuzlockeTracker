# Lockley Three-Day Overhaul — Implementation Plan

Date: 2026-08-24 · Branch: `uat` · Companion to the 2026-08-24 trainer/ROM hack
architecture review. This file is the canonical working copy; work through it
top to bottom, checking off work packages (WPs) as they land.

**Goal:** full trainer coverage for existing games, ROM hacks as a first-class
bonus tier, and Blaze Black shipped as the first hack — plus the system
hardening (schema source of truth, ETL consolidation, identity fixes) that
makes both durable.

---

## Ground rules (every session, every WP)

1. **Migrations are the only way schema changes.** Every change is a new
   self-guarded SQL file in `Backend/migrations/` (follow the pattern in
   `20260629_run_last_opened_backfill.sql`: idempotent `DO $$` block, record
   into `schema_migrations`). Additive only during these 3 days — no drops, no
   renames — so rollback is always just a code revert.
2. **Migrations are single-owner.** Never have two parallel sessions authoring
   migrations. Parallel sessions split backend-vs-frontend or use disjoint
   areas, in git worktrees, merged to `uat` frequently.
3. **Backup before each day's first migration:** `pg_dump` schema + data dumps
   of `trainer_pool`, `trainer_pokemon`, `event_bosses`, `event_locations`,
   `games`, `badges` to a dated folder outside the repo.
4. **Test before prod.** Run migrations against the `pgserver` test fixtures
   (`Backend/tests/conftest.py`) and/or a local restore first; then apply to
   Supabase via psql. Backend tests: `pytest` in `Backend/`. Frontend:
   `npm test` (vitest) and `npm run lint` in `Frontend/`.
5. **Never break guest mode.** Any endpoint change must keep the guest branch
   in `Frontend/src/utils/dataLayer.js` working; test both paths.
6. **Verify against production data, not just previews.** The review's
   placement counts came from ETL validation summaries; re-check live counts
   before and after each data WP.

---

## Day 1 — Foundations

### WP0 · Baseline and safety rail (small, do first)

- Dump the production schema to `Backend/schema.sql` (schema-only pg_dump,
  committed) so the repo finally records reality. Regenerate at the end of
  each day.
- Add `Backend/migrations/apply.py`: runs pending `Backend/migrations/*.sql`
  in filename order via psql using `DATABASE_URL` (env, not hardcoded paths);
  prints applied/skipped. Verify a second run is a no-op.
- **Done when:** `schema.sql` committed; runner idempotent against prod.

### WP1 · Trainer identity hardening (backend)

The single worst foot-gun: parties join by `encounter_name` string
(`Backend/backend.py:2052-2077`) and have no slot/ability columns.

- Migration `20260824_trainer_identity.sql`:
  - `trainer_pokemon` gains `trainer_id integer`, `slot integer`,
    `ability text`, `ability_clean text`, `nature text`.
  - Backfill `trainer_id` where `(encounter_name, version_group_id)` matches
    exactly one `trainer_pool` row; log ambiguous/unmatched counts (expect
    rematch-name collisions — leave those null, endpoint falls back).
- New endpoint `GET /api/trainers/<trainer_id>/party` →
  `get_trainer_party_by_id` in `backend.py`: join by `trainer_id`, order by
  `slot` nulls last, fall back to the encounter-name query when the id has no
  party rows. Keep the old `/api/trainer-party/<name>` endpoint working during
  transition.
- Expose `trainer_id` on script rows (`get_script`, `backend.py:1721+` already
  joins `trainer_pool`) and confirm `/api/trainer-list` rows carry it (they
  do).
- Update the build-6 loader (`load_blackwhite_build6_trainers.py`) to write
  `trainer_id`/`slot` going forward.
- Frontend: `TrainerCard.jsx:74-99` switches to the id endpoint when a
  `trainerId` is present (verify what BossRow/RivalRow actually pass — the
  review found `event_id` used as `trainerId`; thread the real
  `trainer_id` through the script row instead).
- Tests: pgserver integration test for the new endpoint (happy path, slot
  ordering, name fallback); migration backfill test.
- **Done when:** TrainerCard renders parties via trainer_id for a boss and a
  route trainer, both auth and guest; same-named trainers no longer merge.

### WP2 · Phase-0 bug fixes (parallelizable with WP1 except TrainerCard)

- **Guest trainer lists** (broken today): `LocationRow.jsx` already holds
  `gameId`; pass `gameId` + `versionGroupId` into `getTrainerList`
  (`dataLayer.js:256-258`) and send `?game_id=&version_group_id=` for local
  runs; `api.py:235-246` already forwards params. Add a vitest for the guest
  branch. Verify a guest run's trainer panel opens.
- **Unova badges**: extend `BADGE_DEFINITIONS` (`backend.py:79-112`) with the
  Unova set (ids 33+; BW: Trio, Basic, Insect, Bolt, Quake, Jet, Freeze,
  Legend; B2W2 swaps in Toxic and Wave — verify exact names/order in-game
  before committing), add `EVENT_BADGE_MAPPINGS` entries for vgs 11 and 14,
  source badge sprites, and backfill `event_bosses.badge_id` for Unova gym
  events. Verify: BW gym victory creates `attempt_badges`/`pokemon_badges`.
- **Housekeeping**: require admin auth on `/api/debug/trainer-pics`
  (`api.py:262-268`); make `create_run` take `game_id` explicitly instead of
  the `set_active_game` module-global (`backend.py:185-199`).
- **Done when:** guest panels load; a Gen-5 gym win awards a badge; tests
  green.

### WP3 · ETL package scaffold (start Day 1, finish Day 2)

- Create `Backend/etl/` with shared helpers extracted from the build-6
  scripts: psql invocation (env-driven `DATABASE_URL` + `PSQL_PATH`, no
  hardcoded `C:\Program Files\...`), constant normalization (ITEM_/MOVE_/
  species names), preview-CSV writer, loader guard framework (staged temp
  table + row-count/FK/idempotency checks + `--apply`).
- Port the BW/B2W2 build-6 pipeline onto it as the reference implementation.
  Older pipelines migrate opportunistically, not as a blocker.
- Per-version-group manifest (yaml/json): source type, input paths, vg/game
  ids, load build number.
- **Done when:** build-6 preview + loader run end-to-end through
  `Backend/etl/` with no absolute paths.

---

## Day 2 — The full fleet

### WP4 · `location_areas` placement level

- Migration `20260825_location_areas.sql`:

  ```sql
  create table location_areas (
      area_id serial primary key,
      canonical_location_id integer not null,
      area_name text not null,
      area_kind text not null default 'interior', -- gym|interior|floor|outdoor
      sort_order integer,
      unique (canonical_location_id, area_name)
  );
  alter table trainer_pool add column area_id integer;
  ```

- `get_trainers_by_location` (`backend.py:1861+`) left-joins areas and
  returns `area_name`/`area_kind`; `LocationRow.jsx` trainer panel groups by
  area with headers (null area = default "Outside" group).
- Confirm a trainers-only location renders sanely (location row with
  `trainer_count > 0` and an empty encounter pool); fix the encounter section
  empty-state if needed.
- Seed script: create "<City> Gym" areas for every gym city per version group.
- **Done when:** a gym trainer placed into an area shows grouped under the
  city's row, auth + guest.

### WP5 · Placement curation workflow

The unplaced backlog (~2,300 rows across gens; BW 239/615 placed, B2W2
205/813, DP ~320/849, Pt ~320/927 — re-verify live) becomes an admin
workflow, not SQL edits.

- Migration: `curated_trainer_placements(version_group_id, trainer_key,
  canonical_location_id, area_id, decided_at)` — `trainer_key` is the stable
  ETL identity (encounter_name, or the `details` blob's trainer index).
- Admin endpoints (behind existing admin auth): list unplaced trainers per vg
  with map references parsed from `trainer_pool.details` and Serebii
  cross-check suggestions (B2W2 CSVs exist); accept a placement (writes
  `trainer_pool` **and** the curated table); create-area inline.
- Admin page `/admin/placement` modeled on `AdminReports.jsx`: vg selector,
  suggestion chips, one-click accept, bulk accept for exact-match suggestions.
- Loaders apply curated placements after load so re-extraction never loses
  curation.
- Then work the backlog: agent sessions propose placements from map_refs +
  Serebii; human spot-checks in the admin UI. Prioritize BW (Blaze Black's
  base) and the biggest gaps (Pt, HGSS, B2W2).
- **Done when:** placing a batch through the UI raises live location trainer
  counts; a loader re-run preserves them.

### WP6 · Coverage completion (parallel worktree to WP5 ok)

- Write the missing loaders on the WP3 framework: Gen 1 (RB/Yellow build-4
  previews), Gen 4 (DP/Pt/HGSS build-5 previews). Load locally, verify
  counts, then prod.
- Rematch/event opt-in: add `include_rematches`/`include_events` query params
  to `/api/trainer-list` (default off, SQL exclusions become conditional) and
  a small toggle in the LocationRow panel. Stop dropping `is_event` rows
  silently client-side (`LocationRow.jsx:400`).
- Gen 3 re-extraction through `Backend/etl/`: stretch — existing data works;
  do not block Day 2 on it.
- **Done when:** every version group 1-14 has loader-reproducible trainer
  data; rematches viewable behind a toggle.

---

## Day 3 — Variant rails + Blaze Black

### WP7 · The variant model

- Migration `20260826_game_variants.sql`:

  ```sql
  alter table games add column base_game_id integer;
  alter table games add column is_rom_hack boolean not null default false;
  alter table event_bosses add column battle_type text;
  alter table event_bosses add column is_level_cap boolean;
  ```

  Backfill `is_level_cap = true` for gym/E4/champion rows (current hardcoded
  behavior). `pool_game_id` stays dormant; do not reuse it.
- **Reserved id ranges:** hack `game_id` and `version_group_id` start at 1000
  (clear of PokeAPI ids). Blaze Black = game 1001, Volt White = game 1002,
  shared version group 1001, `base_game_id` 17/18 — mirrors the vanilla
  BW pair, so the existing nullable-`game_id` overlay handles BB/VW version
  exclusives exactly as designed.
- Seeding script `Backend/etl/clone_version_group.py --base-vg 11 --new-vg
  1001 ...`: copies `event_locations` (route script) and optionally
  `event_bosses` as an ordering skeleton. New games rows inserted with
  `valid_game = 'hidden'` until launch (verify the exact `valid_game`
  vocabulary — reads filter on `= 'valid'`).
- `get_games` (`backend.py:152-155`) returns `base_game_id`, `is_rom_hack`.
- Frontend:
  - `NewRun.jsx`: vanilla list + a "ROM Hacks" section; hack rows badged
    "Hack of <base>". `LoadRun.jsx` gen filter keeps working (hacks carry
    their base's `generation`).
  - Asset fallback: game logo and trainer sprites resolve hack → base game.
    Replace the `trainerSprite.js:148-158` id-ladder with generation from the
    games/run row (thread `generation` through attempt-page run details).
  - `BossRow.jsx:4-6`: use `is_level_cap` flag from the script row instead of
    the three-string `event_type` list.
- **Smoke test the rails before any BB data:** clone vanilla Black to vg 1001
  as "Test Hack", create a run, verify script/encounters/trainers/badge award
  all work, then remove the test rows.
- **Done when:** the smoke-test clone plays end-to-end identically to Black.

### WP8 · Blaze Black ETL

Inputs: the converted doc texts (RTF → txt conversion verified; keep the
Drayano docs and converted texts **out of the repo** — configure an input
path). Load build 7, on the `Backend/etl/` framework.

- `etl/blazeblack/parse_trainers.py`: "Trainer Rosters" → `trainer_pool` +
  `trainer_pokemon` previews. Location section headers give placement free —
  match against the cloned vg-1001 `event_locations`/`canon_locations` names;
  unmatched headers go to the WP5 curation queue, misspellings ("Striation
  City") via a small alias map.
- `etl/blazeblack/parse_bosses.py`: "Important Trainer Rosters" → boss
  parties with items, movesets, `ability` (Regular) + `ability_clean`, plus
  `event_bosses` rows: order from the cloned skeleton, `battle_type`,
  starter-conditional rival rows via the existing `starter` column
  (Snivy|Oshawott|Tepig columns map to Grass|Water|Fire), `badge_id` from the
  WP2 Unova badges, `is_level_cap` for gyms/E4 and any doc-flagged cap
  fights. Post-game replacement fights ("replaces Backpacker Talon") load as
  ordinary trainers at their location.
- `etl/blazeblack/parse_wild.py`: "Wild Pokemon" → `encounter_pool` keyed by
  game_id 1001/1002. Map BB method labels (Cave/Surf/Fish × Normal/Special,
  grass, shaking) onto the method vocabulary already in `encounter_pool` —
  check live distinct values first. Include the 1% legendary slots.
- Shared normalization map: doc species/move names → `species.name`
  conventions (NidoranM/NidoranF, GrassWhistle-era truncations, curly-quote
  mojibake). Fail loud on unmapped names; the map is data, not code guesses.
- Guarded loaders + validation summary (counts vs doc section counts). Cross-
  check a sample against the manual Blaze Black fills from the user's normal
  Black session.
- **Done when:** preview validation clean; loaded to prod behind
  `valid_game='hidden'`.

### WP9 · Launch verification + stretch

- End-to-end smoke as auth **and** guest: new Blaze Black run from the ROM
  Hacks section → route panels show BB trainers grouped by area → wild
  encounter pools show BB species/methods → gym victory awards the badge
  exactly once → battle compare renders boss movesets → level caps show on
  cap fights.
- Flip BB/VW to `valid_game='valid'`.
- Docs: ADR-0005 (variant model: own game + own vg, copy-then-override,
  reserved ranges), ADR-0006 (trainer identity + placement areas), update
  `.agent-memory/CONTEXT.md` and `features/`. Regenerate `Backend/schema.sql`.
- **Stretch (only if time remains):**
  - `species_overrides` / learnset overrides per version group ("Pokemon
    Changes" + "Level Up Move Changes" docs) feeding moveset inference and
    battle compare — the known fidelity gap for non-boss BB trainers.
  - Collapse the guest script assembly duplication (`dataLayer.js:89-151`
    re-implements `get_attempt_page_data`) onto a single server-driven path.

---

## Sequencing summary

| Day | WPs | Parallel guidance |
|---|---|---|
| 1 | WP0 → WP1 + WP2 (parallel), WP3 start | WP1 backend vs WP2 frontend-leaning; single migration owner |
| 2 | WP3 finish, WP4 → WP5 + WP6 (parallel worktrees) | WP5 admin surface vs WP6 loaders are disjoint |
| 3 | WP7 → WP8 → WP9 | WP8 parsers can be built in parallel with WP7, but load only after the WP7 smoke test passes |

Dependencies that must not be reordered: WP1 before WP8 (BB abilities/slots
need the columns); WP2 badges before WP8 bosses; WP4 before WP5; WP7 smoke
test before WP8 load.

## Out of scope (explicitly)

Gen 6+ vanilla games, additional hacks beyond BB/VW, the Clean-mode variant
as a selectable game (data captured in `ability_clean` only), item/trade
change display, run-status redesign.
