# Split timeline and item library

Implemented locally 2026-09-17; production database is unchanged. Canonical
curated memory: `.agent-memory/features/split-timeline.md`. Complete design and
schema: `docs/split-timeline.md`.

- Attempt feed keeps the original 1126px boundary. At >=1820px, stats and
  splits occupy external left/right gutters. Narrower widths use corner flags
  and overlay drawers; no panel becomes an in-flow column that squeezes feed.
- Eight gyms plus four E4 and champion come from configured boss data. League
  entries have no items. Types use `event_bosses.type_focus`; missing data is
  not guessed.
- `curated_split_items`: exact-game shared admin source of truth keyed by
  stable split; inputs split/item/method, with no collected state.
- `attempt_battle_records`: immutable ordered JSONB party appearance at first
  win plus explicit `died_in_battle`; no Pokemon FK so history survives a
  deleted encounter. Old wins say Party not recorded.
- Battle modal records explicit casualties atomically with victory; guest mode
  mirrors it. Sprites deep-link to current living/Fallen Box and return to split.
- Future final victory screen should reuse these records.
- Schema migration `20260917_split_timeline.sql` is applied locally and is
  idempotent; `Backend/schema.sql` is updated. No factual item rows seeded.
- Verified: 216 backend, 144 frontend, Vite build, targeted lint, live browser
  desktop and 390px checks with no page errors or horizontal overflow.

2026-09-23 extension: `curated_split_item_sources` stores structured Thief,
dust-cloud, conditional and manual sources with optional species/rate/detail/
URL. The panel groups sources compactly and expands each item. The guarded
20260923 migration is applied locally, production untouched, and seeds 68
Lenora items plus only five newly available Burgh items. Focused verification:
9 backend tests, 4 component tests, and Vite build.
