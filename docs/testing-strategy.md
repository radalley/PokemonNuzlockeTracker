# Lockley Testing Strategy

## Current State

No test infrastructure exists today. `Backend/testPokemon.py` and `Backend/guiTest.py` are exploratory scratch scripts, not a test suite — there's no pytest config, no `tests/` folder, and the frontend `package.json` has no `test` script. This is the single biggest coverage gap and the one worth fixing first, both for catching real bugs and because "here's my test suite" is a strong interview asset on its own.

## Recommended Stack

- **Backend:** `pytest` + `pytest-flask` for route tests, a real (or `testcontainers`) Postgres instance for integration tests rather than mocking the DB — the project's logic leans heavily on raw SQL, so mocking psycopg2 would test very little.
- **Frontend:** `vitest` (pairs natively with Vite, near-zero config) + `@testing-library/react` for component/interaction tests.
- **CI:** once GitHub is connected, a simple GitHub Actions workflow running both suites on every push is a quick, high-value addition — flag this as a follow-up.

## Priority 1 — Security & Ownership Boundaries (unit + integration)

This is the most interview-relevant area: it's exactly what the code review flagged as the strongest part of the codebase, and it's easy to break silently.

| What | Test type | Example cases |
|---|---|---|
| `_decode_supabase_jwt` | Unit | valid HS256 token accepted; valid RS256/JWKS token accepted; expired token rejected; tampered signature rejected; missing `sub` claim rejected |
| `require_run_access` / `require_pokemon_access` | Integration | user A cannot read/modify user B's run or pokemon (404, not 403, per current behavior — assert that's intentional); unauthenticated request gets 401; owner gets 200 |
| `get_or_create_user_by_supabase_id` | Unit | new supabase_id creates a user row; existing supabase_id returns the same user without duplicating |

**Coverage target:** every `require_*` helper and `_decode_supabase_jwt` branch — this is small, high-leverage code and should be close to 100%.

## Priority 2 — Core Nuzlocke State Mutations (integration)

The actual game logic — this is what you'd walk an interviewer through.

| What | Test type | Example cases |
|---|---|---|
| `upsert_encounter` / `delete_encounter` | Integration | new encounter creates a pokebank row with correct status; re-encountering updates rather than duplicates; deleting requires ownership (covered by Priority 1, but assert the row is actually gone) |
| `add_to_party_for_attempt` / `remove_from_party_for_attempt` | Integration | party caps at 6 (or whatever the real limit is — confirm in code) and returns `None`/error past that; removing a pokemon frees the slot for reuse |
| `create_bonus_location` / `delete_bonus_location` / `rename_bonus_location` | Integration | this is the most complex single feature in the file (~150 lines) — test create/rename/delete round-trip, and the failure path when `canonical_location_id` doesn't exist |
| `mark_trainer_victory` | Integration | marking a trainer defeated is idempotent (marking twice doesn't double-count) |
| `get_attempt_session_stats` | Unit | stat counts (caught/dead/missed) match a hand-constructed fixture exactly |

**Coverage target:** the documented "happy path" plus one failure case per function. This is where a Nuzlocke run's actual rules live (first encounter only, fainted = dead) — bugs here are bugs in the core premise of the app.

## Priority 3 — Frontend Core Flows (component + interaction)

| What | Test type | Example cases |
|---|---|---|
| `guestStorage.js` | Unit | pure functions — easiest, highest-ROI tests in the frontend. Save/load round-trips data correctly; corrupted/missing localStorage data degrades gracefully instead of crashing |
| `AuthContext.jsx` | Component | renders children once session resolves; redirects or shows logged-out state when no session |
| `Attempt.jsx` (core tracking page) | Interaction | logging an encounter updates the visible list; a smoke test that the page renders without crashing given a fixture run is worth more than it sounds like for a page this size |
| `utils/api.js` | Unit | a failed fetch (network error, 401, 500) is surfaced in a way the UI can handle, not swallowed |

**Coverage target:** smoke-level on every page (renders without throwing), interaction-level on `Attempt.jsx` and `Box.jsx` specifically since they're where the actual gameplay loop lives.

## Explicitly Skipping

- `Load*.py`, `MergeLocations.py`, `temp.py`, `diag_loc.py` — one-off data-seeding scripts, not part of the running application. Not worth test investment; if anything, they're candidates for deletion per the code review/tech-debt notes.
- Trivial getters in `backend.py` (`get_games`, `get_box`, etc.) that are a single parameterized `SELECT` — covered indirectly by the integration tests above; dedicated unit tests would just restate the SQL.
- Visual regression / full E2E (Playwright/Cypress) — valuable eventually, but with zero tests today this is a "later" investment, not a starting point.

## Suggested Order of Attack

1. Stand up `pytest` + a test Postgres DB, write the Priority 1 auth/ownership tests — these double as regression tests for the two critical issues in the code review.
2. Cover Priority 2 (`upsert_encounter`, party management, bonus locations) since that's the core gameplay logic and the best interview material.
3. Add `vitest` + `guestStorage.js` unit tests (cheap, pure functions, immediate value).
4. Wire up GitHub Actions CI once GitHub is connected — running tests on every push is itself worth mentioning in an interview.
