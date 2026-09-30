# Bonus Locations

Bonus locations are user-created extra encounter slots attached to a canonical
location (e.g. "Dreamyard - Monkey"). They share the base row's
canonical_location_id; `secondary_sort_order` distinguishes them (encounter_key
= `<canonical_location_id>:<secondary_sort_order>`).

Behavior established 2026-08-25:

- Bonus rows do NOT inherit the base location's trainer roster. Server:
  `get_attempt_page_data` skips the trainer-count lookup for rows with
  `is_bonus_location` (Backend/backend.py). Guest: the injected bonus row in
  `getAttemptPageData` zeroes trainer_count/available/special
  (Frontend/src/utils/dataLayer.js). UI: LocationRow renders no Trainers
  button on bonus rows and never fetches the trainer list for them; the
  Trainers filter view hides them (zero counts).
- Slot allocation must floor at the base row's own secondary_sort_order:
  BW full-fleet placement gives some canonical rows non-zero secondaries
  (Dreamyard is 234 with secondary 1), and a bonus at the same secondary
  collides on encounter_key/React keys. Server `create_bonus_location` already
  did `max(base, existing)+1`; guest `nextBonusSort` (guestStorage.js) now
  mirrors it, scoped per canonical location, with the base secondary passed
  down from LocationRow.
- Guest bonus rows default their display name to "<base> - Bonus", matching
  server-created rows.

Tests: Backend/tests/test_core_mutations.py
(test_bonus_location_does_not_inherit_trainers, requires games.s_ref/b_ref/
pdb_ref columns now present in tests/conftest.py schema);
Frontend/src/utils/guestStorage.test.js (base-secondary floor test).
Verified live against the Blaze Black guest script (Dreamyard 0/4 canonical,
bonus row trainerless, unique keys).
