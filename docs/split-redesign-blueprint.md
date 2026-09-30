# Split-based attempt page — blueprint (Blaze Black first)

Status: **built locally 2026-09-24/25 (uncommitted on `uat`).** Decisions are in
section 12; the chosen layout is canvas board `ReturnsJump` (section 6).
Section 14 records what was built and where it differs from the plan. Visual mocks live on the design canvas
"Lockley split sections & match flags", page *Split redesign*.

## 1. Goal and scope

Restructure the attempt page around **splits** (gym-to-gym segments, the
"Option B" chapter-band layout) instead of one flat story-ordered feed, so a
player can see, per split:

- the locations newly reachable, including ones reachable *before* the leader
  that the story order files later (Route 4 before Burgh);
- content that opens in **earlier** locations (Route 1 fishing after badge 1,
  Surf tables later, Dreamyard Plasma Grunts after Cress);
- future encounter tables and trainers **highlighted with the split they open
  in**, for planning;
- the split's items (already curated per split) as a planning surface.

Scope: **Blaze Black / Volt White only** (version group 1001, games
1001/1002), behind a per-game gate. Every other game keeps the flat feed.

## 2. Vocabulary

| Term | Meaning |
| --- | --- |
| Split | One entry of the existing split catalogue (`Backend/split_timeline.py`): 8 gyms, E4, champion, keyed `badge:<id>` / `boss:<encounter_name>`. Gains an **ordinal** and a pseudo split `postgame` (D3). |
| Split *S* is open | Every split before *S* is defeated. The **current split** is the first undefeated one (today's "Up next", `SplitTimeline.jsx:156`). |
| `opens_in` | The split in which a thing becomes reachable. `opens_in = badge:34` means "available during Lenora's split", i.e. after beating Cress. |
| Gate | A named, reusable requirement (`surf`, `fishing`, `shaking-grass`) that resolves to one `opens_in` per version group. |
| Home split | The split a location first opens in. The location's row lives in that section. |
| Revisit | Content in a location whose home split is earlier, opening in a later split. Rendered as a compact row in the later section. |

## 3. What exists today (evidence)

- Feed = union of `event_locations` + `event_bosses` (+ bonus rows) ordered by
  one `sort_order` number (`backend.py:2069-2127`). BB order was cloned from
  vanilla BW (`etl/pipelines/clone_version_group.py:70-72`).
- Splits are a derived catalogue (`split_timeline.py:9-47`); items attach by
  `split_key` text (`curated_split_items`, `curated_split_item_sources`).
- **No availability data anywhere.** `encounter_pool` has `area`, `method`,
  `condition` (seasons only) but no gate; `trainer_pool` has only
  `is_rematch`/`is_event`; the BB source docs carry no gating
  (Drayano 3.1 `Wild Pokemon.txt`, `Trainer Rosters.txt`).
- The only gating facts are prose in `docs/blaze-black-item-seed-analysis.md`
  (lines 18-26) and the raw wild doc's preamble (shaking grass after badge 1).
- `available_trainer_count` today means "not yet defeated", not reachable
  (`backend.py:1843`).

Consequence: availability is **curated data**, seeded from the known facts
and extended in admin edit mode.

## 4. Data model

Two additive tables, keyed by stable text (never by `encounter_id`, which an
ETL `--replace` renumbers), mirroring the `curated_trainer_placements`
pattern.

```sql
-- A named requirement and where it opens, per version group.
create table split_gates (
  version_group_id integer not null,
  gate_key         text    not null,   -- 'surf', 'fishing', 'shaking-grass'
  label            text    not null,   -- 'Surf', 'Super Rod', 'Shaking grass'
  opens_in         text,               -- split_key or 'postgame'; NULL = unknown yet
  default_methods  text[]  not null default '{}',  -- registry keys this gate governs
  note text, source text,
  primary key (version_group_id, gate_key)
);

-- Exceptions to the derived defaults.
create table curated_availability (
  version_group_id integer not null,
  subject_kind     text    not null
    check (subject_kind in ('location', 'area', 'table', 'trainer')),
  subject_key      text    not null,
  opens_in         text,               -- explicit split_key / 'postgame'
  gate_key         text,               -- or a gate
  note text, source text,
  decided_at timestamptz not null default now(),
  primary key (version_group_id, subject_kind, subject_key),
  check (opens_in is not null or gate_key is not null)
);
```

Subject keys:

| kind | key | example |
| --- | --- | --- |
| location | `<canonical_location_id>` | `9` (Route 4) |
| area | `<lid>\|<area>` (encounter area label) | `237\|Inside` |
| table | `<lid>\|<area or ''>\|<method>\|<condition or ''>` — the table identity `load_encounters.py:132` already uses | `3\|\|dark-grass\|` |
| trainer | `trainer_pool.encounter_name` | `TRAINER_BB_PLASMA_GRUNT_PLASMA_GRUNT` |

CSV round-trip like placements: `etl/curation_data/vg1001_availability.csv`
and `vg1001_gates.csv`, loaded by a new `sync_curated_availability.py`.

### Resolution (pure, `Backend/split_availability.py`)

Splits get ordinals from the catalogue (`postgame` = last + 1). Then:

1. **Default location split** = the first split whose boss `sort_order` is
   ≥ the location's `sort_order` (Route 4 at 10 → Elesa at 12.2).
2. **Location** = explicit location rule, else the default.
3. **Area** = explicit area rule, else its location.
4. **Table** = explicit table rule, else `max(area, gate of its method)`.
5. **Trainer** = explicit trainer rule, else its trainer area/location.
6. **Home split of a location** = `min` over the location and its areas (so
   Pinwheel Forest lands in Lenora's section via *Outside*).
7. A gate with `opens_in` NULL resolves to **unknown**: rendered as a dashed
   "Surf · split not set" chip, never guessed.
8. Bosses keep their story position: a boss belongs to the first split whose
   own boss `sort_order` is ≥ its own.

Everything above is a pure function of (catalogue, script, rules) and is
unit-tested without a database.

### Blaze Black seed (only facts already in the repo, plus the user's two examples)

| Rule | Value | Source |
| --- | --- | --- |
| gate `shaking-grass` (`grass-spots`, `cave-spots`) | `badge:34` | raw wild doc preamble line 2; `encounter_methods.py:19` |
| gate `fishing` (`fish`, `fish-spots`) | `badge:34` (Super Rod on Route 3, reached in Lenora's split) | seed analysis :24-25 |
| gate `surf` (`surf`, `surf-spots`) | **NULL — to curate** | seed analysis :24 says only "unavailable through Burgh" |
| table `3\|\|dark-grass\|` (Route 1 dark grass) | gate `surf` | seed analysis :23 |
| area `235\|B1F` (Wellspring B1F) | gate `surf` | seed analysis :26 |
| area `237\|Outside` | `badge:34` | seed analysis :20 |
| area `237\|Inside` | `badge:35` | seed analysis :21 |
| trainers `TRAINER_BB_PLASMA_GRUNT_PLASMA_GRUNT`, `_2` (Dreamyard) | `badge:34` | user, 2026-09-24 |
| location `9` (Route 4) | `badge:35` | user, 2026-09-24 |

Still to curate with the user: which split Surf opens in; the four Pinwheel
`TEAM_PLASMA_GRUNT` trainers (Inside?); every location after Burgh.

## 5. Payload

`get_attempt_page_data` and `/api/guest-script` (guest parity) gain, for
split-layout games only:

- `splits`: `[{split_key, ordinal, kind, label, leader, type_focus, color,
  level_cap, battle_type, boss_event_ids}]` (+ `postgame`).
- Script location rows: `home_split`, `revisits: [{split_key, tables:[...],
  areas:[...], trainer_ids:[...]}]`.
- `pool_tables` rows: `opens_in`, `opens_gate`, `opens_unknown`.
- Trainer list rows (`/api/trainer-list`): `opens_in`, `opens_gate`.
- `split_gates` for labels.

The current split is derived client-side from defeats (no new stored state).

## 6. Page anatomy (Option B)

**User decisions 2026-09-24:** Option B chapter bands approved; content that
opens in earlier areas goes **at the top, directly under the split banner**
(before New areas); returning trainers are shown **grouped under their area**
(T2 presentation, never a flat list with location tags). Three layouts for
that returns block are on the canvas (area cards / tile strip / filtered
location rows); the diagram below predates the returns-first order.

**Chosen 2026-09-24: "B revised" (canvas board `ReturnsJump`).** Under the
banner, two side-by-side lists, no dropdowns or inline panels:

- **New encounters**: one entry per earlier area, listing the newly open
  *methods* by name with method icons (never "tables"), plus the area's
  encounter state (open areas highlighted and listed first; used ones muted,
  rare slots like "Jirachi 1%" called out).
- **New trainers**: one entry per earlier area with trainer chips
  (class, max level) and a beaten count.
- **Every entry is a jump link** to the area in its **home split**: the
  home split expands, the page scrolls to the location row, and its panel
  opens on the new content. Trainers: the trainer panel, with the returning
  trainers under a "New in <leader>'s split" divider and highlighted (board
  `JumpDreamyard`). Encounters: the encounter panel, with the new methods'
  tabs badged NEW and the first one selected (board `JumpRoute1`). A sticky
  "Back to <current split>" pill returns to the jump source.
- Consequence: trainers are **not** rendered twice; the list is navigation
  only. This settles D1 (T1 storage and cards, jump-list presentation) and
  D6 (jump, not expand in place).

```
Header  (party, Box, Edit)
Sticky strip: current split, e.g. "Split 2 · Lenora · Normal · Cap 20"
─ Split 1 · Cress  [collapsed band, ✓ defeated]            ▸ expand
─ Split 2 · Lenora [chapter band: leader, type, cap, format flag, progress]
   Items this split  (68 · Thief 43 · Dust clouds 28 · Conditional)  ▸
   NEW AREAS            Route 3 · Wellspring Cave (1F) · Nacrene City ·
                        Pinwheel Forest (Outside)          ← LocationRows
   BACK TO EARLIER AREAS
     Route 1   Fishing + Shaking grass open · encounter still open   ← highlighted
     Route 2   Shaking grass open · encounter used                    ← muted
     Dreamyard 2 Plasma Grunts · Shaking grass (Jirachi 1%)
   Rival / story fights in story order
   Boss card: Lenora (Double, cap 20)
─ Split 3 · Burgh  [band] …
Right rail: badge medallions (done ✓, current ringed, future outlined) → jump
```

- Past splits collapse to their band (D5); current is open; future splits are
  open but dimmed, for planning.
- Revisit rows are **nuzlocke-aware**: bright when the location's encounter
  is still unused, muted when used. Clicking one expands the location row in
  place (same component, same state) or jumps to it (D6).
- The standalone right-side `SplitTimeline` panel is retired for BB: its
  items move into the sections and its navigation into the rail.

## 7. Encounter tables with future-split highlighting

Inside a location's tables (existing `EncounterTables.jsx` method tabs):

- An **open** table renders as today.
- A **future** table keeps its rows visible but dimmed, with a chip in that
  split's type colour: "Opens in Lenora · after badge 1" / "Opens with
  Surf · split not set". The method tab carries a small medallion dot.
- Claiming from a future table is blocked (D2): the location's one encounter
  can't be spent on something not yet reachable. A future table still counts
  for the dupe check preview.
- The rare strip (legendary overlays/statics) inherits its host table's state.

## 8. Trainers — two options (D1)

- **T1 · by area, future highlighted.** Trainers stay in their location panel
  grouped by area; future ones render locked with the split chip ("Opens in
  Lenora"). One card, one defeat state. The Lenora section's Dreamyard
  revisit row says "2 Plasma Grunts" and expands the Dreamyard panel.
- **T2 · listed under the split.** The split section gets a "Trainers
  unlocked this split" group with full cards tagged by location; the home
  location shows a ghost line "2 more return in Lenora's split →".

**Recommendation: T1 storage + T2 presentation.** A trainer has exactly one
card component instance backed by one record; the split section's roll-up
renders the *same* cards (shared state keyed by `trainer_id`), and the home
panel shows the ghost line. Counts: the location pill counts only trainers
open so far; the split band counts trainers open in that split.

## 9. Items

`curated_split_items` already hang off `split_key`, so each section shows its
items directly under the band (collapsed summary, expandable to today's
grouped panel). "Plan ahead" peeks at the next split's items without scrolling.

## 10. Admin curation (edit mode)

With the header Edit toggle on (`EditModeContext`):

- Location rows, area pills, table cards and trainer cards get an **Opens in**
  control: a popover of split medallions, the gates, "Inherit (…)" and a note.
- Writes `POST /api/admin/availability {subject_kind, subject_key, opens_in |
  gate_key, note}`; `DELETE` reverts to inherit. Gate editor: one row per gate.
- Changes re-resolve and re-render immediately; CSV export for the repo.

### Game flags panel (replaces the debug panel)

The admin "Debug" item in the attempt header menu opens today's
`Frontend/src/components/PaletteDebugPanel.jsx` (CSS token swatches, species
sprite and trainer-pic validity checks). Per the user, **clear it and rework
it into a Game flags panel**: one row per gate for the current version group
(`split_gates`): label, governed methods, and an **Opens in** split picker
(medallions, plus "Not set"). Saving writes `split_gates.opens_in` via an
admin route; the page re-resolves availability immediately. Future flags
(e.g. Strength, Dive, story events) are new gate rows, not new UI. The
sprite/palette checks are dropped (reinstate on an admin page only if the
user asks).

## 11. Gating and parity

- `SPLIT_LAYOUT_VERSION_GROUPS = {1001}` (backend) and a matching frontend
  constant, like `DAMAGE_CALCS`. Other games: payload unchanged, flat feed.
- Guest runs: availability is reference data, so `/api/guest-script` returns
  the same resolved fields; defeats come from `guestStorage` as today.
- Split progression and badges are unchanged; availability is display and
  claim-gating only.

## 12. Decisions

Settled with the user 2026-09-24:

- **D1 Trainers**: stored and rendered once in their home area (grouped by
  area); the split's "New trainers" list is navigation only (section 6).
- **D2 Future tables: blocked.** A table/method not yet open cannot be used
  to log the location's encounter; it stays visible (dimmed, split chip).
- **D3 Sections**: 8 gyms, then **League** (Elite Four x4 + N 32.5 +
  Ghetsis 32.6), then **Postgame**. Postgame (section and rail medallion)
  stays **hidden until Ghetsis is defeated** (confirmed by the user). Alder
  (the catalogue's `champion` split, sort 46.1, cap 100) lives **inside
  Postgame**, alongside everything after Ghetsis in story order.
- **D4 Surf timing is admin data**, not decided here. The `surf` gate ships
  with `opens_in` NULL ("split not set") and the user sets it from the Game
  flags panel (section 10) when they reach it.
- **D5** Past splits collapsed to their band by default (as mocked).
- **D6 Jump**, not expand in place (section 6).
- **Trainer availability** starts from a best guess (location default +
  the seed in section 4) and the user corrects it in admin edit mode while
  playing. No up-front curation pass is required before shipping.

Still open (raise during the build, default in brackets):

- **D7** Bonus locations vs areas once areas carry `opens_in` [keep bonus
  locations unchanged].
- **D8** One encounter per location vs per area [per location, as today].
- **D9** Master/Encounters/Trainers filter inside sections [keep the filter,
  applied within each section].

## 13. Build phases

1. **Data**: migration (two tables), `split_availability.py` resolver + pure
   tests, BB seed CSVs from section 4, sync pipeline.
2. **Payload**: splits + resolved fields in page data and guest-script,
   gated to vg 1001; backend tests on BB fixtures.
3. **Sections**: `buildSplitFeed` (pure, tested), `SplitSection`, chapter
   band, sticky strip, medallion rail; flat feed untouched for other games.
4. **Encounter highlighting**: table states, chips, claim gating, revisit
   rows.
5. **Trainers**: availability chips, roll-up, counts.
6. **Items** in sections; retire the right panel for BB.
7. **Admin curation**: Opens-in picker in edit mode, the Game flags panel
   replacing `PaletteDebugPanel`, admin API, CSV export.
8. **Ongoing curation** by the user while playing (no blocking pass).

## 14. As built (2026-09-25)

- **Data**: `Backend/migrations/20260925_split_availability.sql` (key
  `split_availability_v1`; `split_gates`, `curated_availability`, the BB
  seed from section 4 plus `location 234 -> badge:33` so Dreamyard's first
  trainers sit before the Striaton Gym; `ON CONFLICT DO NOTHING` so admin
  edits survive). Applied to the local dev DB; production untouched.
  CSV round-trip: `Backend/etl/pipelines/sync_curated_availability.py`
  with `etl/curation_data/vg1001_gates.csv` and `vg1001_availability.csv`.
- **Resolver**: `Backend/split_availability.py` (pure `build_sections` +
  `resolve`, DB loaders, `decorate_page`, `annotate_trainers`, admin
  `save_rule`/`delete_rule`/`save_gate`). Differences from section 4:
  sections are derived from the script's boss rows (not the catalogue),
  the League is one section (`league`) closing with the last boss in the
  Elite Four's integer sort slot (Ghetsis 32.6), `postgame` reveals after
  it and holds Alder; a trainer with no rule defaults to its location's
  **home** split (earliest access), not the story-order default, so an
  uncurated roster stays with its row. Tests:
  `Backend/tests/test_split_availability.py`.
- **Payload**: `get_attempt_page_data` and `/api/guest-script` gain
  `splits`, `split_gates`, per-row `home_split`, `opens_*`, `areas`,
  `revisits` (with `is_defeated` on returning trainers), `trainer_splits`;
  pool_tables rows gain `opens_in`/`opens_gate`/`opens_unknown`/
  `opens_rule`; `/api/trainer-list` rows gain `opens_in`. Admin:
  `POST/DELETE /api/admin/availability`, `PATCH /api/admin/gates`.
- **Frontend**: `utils/splitFeed.js` (pure feed, availability helpers),
  `components/SplitSection.jsx` (band, items, returns jump lists, rows),
  `SplitRail.jsx`, `SplitSections.css`, `OpensInPicker.jsx`,
  `GameFlagsPanel.jsx` (replaces the deleted `PaletteDebugPanel.jsx`;
  header menu item renamed "Game flags"), `SplitItems.jsx` +
  `utils/splitItems.js` (shared with `SplitTimeline`, which other games
  keep). `Attempt.jsx` switches layouts on `data.splits`; `LocationRow`
  gets `id="location-<encounter_key>"`, the openRequest jump, later-split
  trainer groups with locks, blocked future tables, admin pickers;
  `EncounterTables` gets availability chips, NEW badges, focus, admin
  hooks; `TrainerCard` gets `lockedLabel`. Guest parity in
  `dataLayer.getAttemptPageData`.
- **Not done / follow-ups**: D7-D9 kept their defaults (bonus locations
  unchanged, one encounter per location, filter applied within sections).
  Recorded parties show in a beaten split's band only when a battle record
  exists. Surf's split is still unset (Game flags).

### Pinwheel Forest split (2026-09-25)

D7 resolved for this one location: `Backend/migrations/20260925_bb_pinwheel_inside.sql`
makes the interior its own script row, **Pinwheel Forest (Inside)**
(canonical 504, vg 1001, sort 8 like the outer row; the name orders it
second). Interior wild tables (incl. Virizion's Rumination Field) move to
504, the outer road keeps 237, and each row's single main area loses its
label. Trainers: vanilla ROM zone 155 stays outside (Forrest, Audra,
Sammy, Millie, Mayo & May, Nicholas, Eva); zone 154 plus the story grunts
and, by the game's layout, Lee/Irene/Miguel move inside (13). Placements
are written to `curated_trainer_placements` so re-extraction keeps them.
Availability: area rules replaced by location rules 237 -> badge:34,
504 -> badge:35. Existing attempts' "Inner Pinwheel Forest" / interior-family
bonus slots became the new row's encounter (bonus rows retired, not
deleted). `import_bb_sheet.py` maps the sheet's inner column to 504.
Applied to the local dev DB; production untouched. If Audra, Lee, Irene or
Miguel are on the wrong side, move them via `curated_trainer_placements`
(the admin placement page only handles unplaced trainers).
