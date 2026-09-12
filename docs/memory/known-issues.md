# Known Issues And Operational Notes

## BW venue parity for Blaze Black (deferred 2026-08-25)

Vanilla vg 11 gained venue script rows (Royal Unova 501, Big Stadium &
Small Court 502, Black City 503, Pokemon League 226) during full-fleet
placement. The Blaze Black script (vg 1001, cloned earlier) does NOT have
these rows, and the BB ETL's 355 trainers do not include stadium/cruise
rosters (Drayano docs don't cover them). If BB should mirror the venues,
add the script rows for vg 1001 and decide whether hack venue trainers
inherit from vanilla. Low priority; BB's placed set (284/355) is
doc-driven and its remaining 71 are boss variants.

## Attempt page background-refresh contract (2026-08-25, commit fd00e6c)

Recording a victory (or starter/structure change) no longer unmounts the
attempt page into "Loading..." -- refetches of the already-displayed
attempt reconcile in the background (Frontend/src/pages/Attempt.jsx:
loadedIdentityRef + loadSeqRef; savedEncounters writes versioned via
encountersVersionRef so stale snapshots cannot clobber mid-flight
encounter edits). The loading screen appears only for initial loads and
attempt switches. Preserve this contract when touching the page: no
setAttemptLoaded(false) on same-identity refetches, and any new writer
of savedEncounters must bump encountersVersionRef. Deferred low-severity
edge (review-confirmed): sibling LocationRows sharing an event_id (bonus
location duplicating a canonical one) keep independently loaded trainer
lists, so a victory in one open panel leaves the other panel stale until
a full page load; re-clicks are idempotent server-side.

## Wild parser section drops (found 2026-08-25 in play, fixed commit 253ea54)

The user's Blaze Black run surfaced an empty Starter pool; the dig found
the wild parser had silently lost or misattributed ~270 rows across four
doc dialects: (1) a jammed LEGENDARY state machine (unconditional
continue on unmatched species lines -- split-game formats, 'Virizion.
Level 56') swallowed whole sections (Route 11, Liberty Garden); (2) the
slot stage consumed the next section's header when a static block had no
slot line, leaking Twist Mountain into Mistralton Cave and Undella Town
into Giant Chasm; (3) single-label lines ('Sand:', 'Shaking Grass:')
never matched, dropping Desert Resort and Relic Castle entirely; (4)
wrapped slot lists lost their continuation line. All fixed in
parse_wild.py with regression tests; dev reloaded at 2,312 rows. New
`fill_encounter_gaps` pipeline inherits vanilla pools for doc-absent
locations (the Starter fix) and is now a runbook step after
load_encounters. Lesson: preview validation compared totals against the
manifest's own expected count, so systematic parser drops were
self-consistent and invisible -- coverage-style checks (vanilla location
diff) caught it.

## Supabase project DNS dead (observed 2026-08-25)

`glepdgmehmumsjoskhcp.supabase.co` returns NXDOMAIN from local AND public
resolvers while supabase.co resolves fine — the classic paused-free-tier
symptom. Effects: sign-in fails with "Failed to fetch"
(AuthRetryableFetchError status 0), and any browser with a cached session
loads slowly because apiFetch awaits supabase.auth.getSession() before
every call while token refresh retries against the dead host. Fix: restore
the project in the Supabase dashboard (user action). Interim speed fix:
delete the sb-* localStorage keys for localhost:5174.

## Override-layer gate findings (2026-08-25, fixed in commit 7fce5b6)

An 11-agent adversarial review confirmed: (1) the '-' learnset delta wiped
doc-added moves at its level (Natu's Safeguard); (2) the no-game-context
moveset pick returned max(values) which becomes vg 1001 post-load —
reserved range now excluded from the vanilla pick; (3) unresolved member
restrictions silently applied to all members — now loud, which surfaced
Rotom form lines wrongly applied to base Rotom and a Mineshao typo.

## Launch-gate review findings (2026-08-25, all fixed in WP9 commit edc604e)

A 14-agent adversarial review of the overhaul diff confirmed three defects,
fixed the same day: (1) reserved hack version groups (1000+) leaked
wrong-generation movesets/move stats — resolvers now map to the base game's
version group via `_moveset_version_group_for`; (2) `get_db` leaked pooled
connections when post-getconn setup failed — now `putconn(close=True)`;
(3) `load_trainers`' already-loaded guard was (vg, build)-scoped and could
silently double trainers — now version-group-wide. Refuted (not real): a
claimed full-outage on deploy-before-migrations, and a claimed clone
party-duplication via encounter_name. Note the deploy-before-migrations
ORDER in the runbook still stands regardless.

## Local backend availability can mimic data or auth failures

A stopped or stale local backend previously caused the menu feed, game lists,
and new-game data to appear unavailable. Restarting the backend restored local
database loading. Check API reachability and backend logs before changing auth
or menu state logic for the same symptom.

## Badge architecture smoke test

The normalized badge migration and targeted tests passed, but an authenticated
browser/API smoke test still depends on the local backend running. Confirm that
script rows expose `boss_event_id` and `badge_id`, then verify a gym victory
creates attempt and party Pokemon badge rows exactly once.

## Verified defects from the 2026-08-24 trainer/ROM hack review

Confirmed directly against code during the trainer-data architecture review:

- RESOLVED 2026-08-24 (WP2, commit ba61f60): guest trainer lists now send
  `game_id` + `version_group_id`; the backend also derives the version group
  from `game_id` alone.
- RESOLVED 2026-08-24 (WP1, commit 5cf1fe0): trainer parties are now keyed by
  `trainer_id` via `GET /api/trainers/<trainer_id>/party` and
  `trainer_pokemon.trainer_id` (migration `20260824_trainer_identity.sql`,
  backfilled 17,664 rows; 35 legacy gen-3 rival orphans remain null and fall
  back to the encounter-name match). The legacy name-keyed endpoint still
  exists for compatibility but TrainerCard no longer uses it when a
  trainerId is present.
- RESOLVED 2026-08-24 (WP2, commit ba61f60): Unova badges 33-42 defined and
  mapped for version groups 11/14 (migration `20260825_unova_badges.sql`,
  19 gym events mapped on dev; badge sprites 33-42 already existed).
- PARTIALLY RESOLVED 2026-08-24 (WP1): `trainer_pokemon` now has
  `trainer_id`, `slot`, `ability`, `ability_clean`, `nature` columns; slot
  codifies prior insertion order (`pk_id` sequence). The species join is
  still by name string.
- SECURITY, unresolved: `Backend/loadPG.py:8-14` contains plaintext Postgres
  credentials (host/port/database/user/password) committed to the repo. It is
  a legacy one-shot SQLite-to-Postgres migration script, not part of the
  current pipeline. Rotate that password and remove the literals; note the
  value stays in git history, so rotation is the actual fix.
- ETL reproducibility, partially resolved (WP3): `Backend/etl/` is env-driven
  and the Gen 5 loaders run anywhere. The preview *builders* (ROM/decomp
  extraction) and the Gen 1-4 loaders/updaters still hardcode absolute paths
  to this machine (`C:\Program Files\PostgreSQL\18\...`, OneDrive ROM paths,
  `C:\Users\radal\Lockley Game Decomps\...`).
- Trainer placement, not extraction, is the coverage bottleneck: per the ETL
  validation summaries, BW has 239/615 trainers bound to a canonical location,
  B2W2 205/813, DP ~320/849, Platinum ~320/927 (verify against production).
