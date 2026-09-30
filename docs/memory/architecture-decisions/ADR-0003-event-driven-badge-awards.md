# ADR-0003: Event-Driven Normalized Badge Awards

- Status: Accepted
- Scope: Gym victories and badge ownership

## Decision

Badge identity belongs in data rather than an in-page trainer-name map.
`event_bosses.badge_id` identifies the badge granted by a scripted fight.
Winning that event inserts normalized records into `attempt_badges` and
`pokemon_badges` for the current party. Replaying an already-recorded victory
does not award the badge to a later party.

Legacy text badge columns remain compatibility surfaces while reads transition
to the normalized relationships.

## Evidence

- Schema and mutation ownership: `Backend/backend.py`
- Victory route: `Backend/api.py`
- Frontend event propagation: `TrainerCard.jsx`, `BossRow.jsx`, `RivalRow.jsx`
- Guest parity: `Frontend/src/utils/guestStorage.js`
