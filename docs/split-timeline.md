# Split timeline: design and schema

Implemented locally 2026-09-17. Approved design: `lockley-final-preview.html`
from the 2026-09-16 design conversation. The victory recap remains future work.

## Interface

The attempt feed alone occupies the existing 1126px root boundary. At viewport
widths of 1820px and above, stats live in the left outer gutter (250px) and
splits in the right outer gutter (330px). Both are positioned beside the sheet
and move with normal page scrolling; Splits has no nested desktop scrollbar.
They must never become columns that shrink the encounter/trainer sheet.
Below this threshold, corner tabs open side drawers; this is a basic fallback,
not the completed mobile design. Desktop Stats never turns into an edge tab
when minimized; it can be reopened from the header menu. Existing Box page
stats layout is unchanged.

Each gym split shows a leader portrait, `type_focus`, status, historical party
sprites, and compact item source groups. Thief, Dust clouds, Conditional and
manual groups collapse independently; each item expands to its Pokemon/source
and rate. Items with multiple methods share one parent and appear in each
relevant group. Defeated portraits are grey; only Pokemon that
died in that specific battle are grey and marked with a cross. Their earlier
appearances retain colour. All / Parties / Items filters retain every boss
heading. Filter choice persists for the attempt in sessionStorage.

Four Elite Four records and one Champion record follow the gyms, with no item
tables. The catalogue follows actual configured game content, not hardcoded
preview names: local Blaze Black currently yields 8 gyms + 4 E4 + Alder.
N/Ghetsis and optional postgame trainers are not relabelled as the Champion.
E4/champion type values currently missing in the data show the role as a
fallback; populate `event_bosses.type_focus` from verified content later.

Admin item forms expose exactly **split, item, method**. Item is a free-text
name; method accepts text such as `Thief - Audino 5%`. Add appends records;
Edit/Remove correct existing
records. There are no collected flags, counts, quantities or party headings.
The library describes repeatable availability, including Thief sources.

## Schema

Authoritative, replay-safe migration:
`Backend/migrations/20260917_split_timeline.sql` (`split_timeline_v1`).

### curated_split_items

| Column | Type / constraint |
| --- | --- |
| item_record_id | bigint identity primary key |
| game_id | integer, required, FK games.game_id |
| split_key | text, required, 1–240 characters |
| item_name | text, required, trimmed length 1–100 |
| method | text, required, trimmed length 1–500 |
| created_at / updated_at | timestamptz, default current_timestamp |

Unique `(game_id, split_key, item_name, method)` makes duplicate adds safe to
retry. Records are scoped to the exact game, never implicitly shared between
Blaze Black, Volt White, or vanilla Black. Keys use `badge:<badge_id>` for gyms
(so starter variants share the same preparation list), otherwise
`boss:<trainer_pool.encounter_name>`. The API permits items only for gym splits.
No event/trainer FK: ETL-generated IDs must not own or delete admin curation.

### curated_split_item_sources

Migration `20260923_blazeblack_split_item_sources.sql` adds child source rows:
identity `item_source_id`; cascading `item_record_id`; replay-safe
`source_key`; `method_kind` constrained to thief, dust_cloud, conditional or
manual; optional `source_species_id`, `chance_percent`, `source_detail`, and
`source_url`; plus `sort_order`. Species is descriptive rather than an FK so
durable curation survives partial fixtures and content reloads.

The initial exact-game Blaze Black seed records 68 Lenora items and five
newly available Burgh items. Lenora contains 43 ordinary Thief names,
conditional Colbur, and 28 dust-cloud names with four overlaps. Burgh contains
only Kebia Berry, King's Rock, Mental Herb, Occa Berry and Rindo Berry; items
already available remain under their earliest split. Surf-gated sources are
excluded. The seed and legacy-manual backfill are idempotent.

### attempt_battle_records

| Column | Type / constraint |
| --- | --- |
| battle_record_id | bigint identity primary key |
| attempt_id | integer, required, FK attempts.attempt_id ON DELETE CASCADE |
| trainer_id | integer, required; recorded content identity |
| boss_event_id | nullable integer; recorded content provenance |
| split_key | nullable text; present for split bosses |
| party | required jsonb array |
| recorded_at | timestamptz, default current_timestamp |

Unique `(attempt_id, trainer_id)` plus index `(attempt_id, split_key)`.
Each array member freezes `slot`, `pokemon_id`, `species_id` (including form),
`species_name`, `nickname`, `shiny`, `gender`, and `died_in_battle`. No Pokemon FK:
deleting an encounter must not erase its historical appearance. Reads enrich
members with `available`, permitting links only while the Pokemon still exists
in that attempt. Both tables have RLS enabled with no client policies; Flask
auth/admin/ownership gates own access through the privileged backend connection.

## Recording and navigation

`mark_trainer_victory` locks the attempt row, checks game/trainer membership,
validates up to six unique participant IDs and a fainted subset, and resolves
appearance from server-side Pokebank rows. The modal retains the battle roster
even if a participant has left the active party. Its `Fell in this battle`
checkboxes explicitly identify casualties. Snapshot, victory, badge/counters,
fallen status and party removal commit together. Repeated wins do not replace
the snapshot or reapply deaths. Guest runs mirror this in `battle_records`
under the existing attempt storage key and expose it in local-data exports.

Prior wins without snapshots say `Party not recorded`; current species cannot
reconstruct historical evolution or death timing. A win with no party records
an empty array. No automatic historical backfill is performed.

Sprite links open `/box/:runId/:attemptId?pokemon=<pokemon_id>`, select/reveal
the living or fallen Pokemon, and carry a Back to split route/hash. The Box
shows current identity; the split retains historical appearance. The same
records and catalogue are intended for the future final victory timeline.

## API and files

- Public `GET /api/games/:gameId/splits?starter=...`: catalogue and shared items.
- Owner-only `GET /api/runs/:runId/attempts/:number/battle-records`.
- Admin-only `POST/PATCH/DELETE /api/admin/split-items`.
- Existing trainer-victory POST adds optional `participant_ids` and `fainted_ids`.
- `Backend/split_timeline.py`: catalogue, curation, snapshot helpers.
- `Frontend/src/components/SplitTimeline.jsx` / `.css`: panel, filters, editor.
- `Frontend/src/utils/useDockedPanels.js`: gutter/drawer breakpoint.

## Verification and rollout

Both migrations are applied to the local database; production was not changed.
Apply them before deploying API code.

Verified: 216 backend tests; 143 frontend tests plus an added Box deep-link
test; production Vite build. New integration tests cover replay, evolution,
explicit deaths, deleted Pokemon, wrong-attempt members, old wins, game scope,
stable curation keys, admin access and owner-only records. Component tests
cover filters, League entries without item tables, historic links and admin form.
Live browser checks at 1920px and 390px: no horizontal overflow; desktop
stats x=136–386, splits x=1534–1864, main feed x=426–1494. Both desktop
panels use normal document scrolling; narrow tabs retain independent drawer
scrolling.

Item-source verification on 2026-09-23: 9 split-timeline backend tests and 4
focused component tests pass, including migration replay, 68/5 split counts,
overlapping Everstone sources and conditional Colbur. Vite production build
passes. The in-app browser could not reuse the user's authenticated Chrome
session, so this change did not repeat the earlier live geometry check.
