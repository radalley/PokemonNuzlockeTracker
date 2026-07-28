# Code Review: Lockley Backend (`api.py`, `backend.py`)

### Summary
The live, route-reachable code path is in solid shape: every mutating/data route runs through `require_auth` / `require_run_access` / `require_pokemon_access` ownership checks, and the SQL those routes actually call is properly parameterized — no exploitable injection found. The issues below are real but fixable in an afternoon, and most come from leftover legacy code rather than the current architecture.

### Critical Issues

| # | File | Line | Issue | Severity |
|---|------|------|-------|----------|
| 1 | `api.py` | 573-574 | `app.run(debug=True)` — Flask's interactive debugger allows remote code execution if this ever runs in production. The empty `Procfile` (see ADR-001) means it's not guaranteed gunicorn is what actually serves this in prod. | 🔴 Critical |
| 2 | `api.py` | 360-367 | `/api/debug/trainer-items` has no auth check and dumps raw DB rows. Debug routes like this shouldn't ship to a public deployment. | 🔴 Critical |
| 3 | `backend.py` | 231, 266, 1148 | `drop_pokemon`, `get_attempts`, and the helper at line 266 build SQL with f-string interpolation (e.g. `f'delete from pokebank where pokemon_id = {pokemon_id}'`) instead of parameterized queries — classic SQL injection pattern. Good news: these functions aren't imported by `api.py`, so they're not reachable through the live API today. Bad news: they're one accidental import away from becoming exploitable. | 🟡 High (currently dead code) |

### Suggestions

| # | File | Line | Suggestion | Category |
|---|------|------|------------|----------|
| 1 | `api.py` | 51 | `_decode_supabase_jwt`'s JWKS fallback does `except Exception: return None` — swallows real errors (e.g. Supabase being unreachable) as if the token were simply invalid. Log the exception before returning None. | Correctness |
| 2 | `api.py` | 152-153, 248, 261, 510 | Several routes do raw `data['key']` access on the JSON body with no validation, so a malformed request raises an unhandled `KeyError` → ugly 500 instead of a clean 400. Worth a small `validate_required(data, [...])` helper. | Correctness |
| 3 | `api.py` | 26 | `CORS(app, supports_credentials=True)` has no explicit `origins=` allowlist. Worth locking this to your actual deployed frontend domain(s) rather than the flask-cors default. | Security |
| 4 | `backend.py` | 68, 215-334, 1140-1148 | The global module-level `state` dict and the functions that mutate it (`set_active_run`, `new_attempt`, `get_party`, `add_pokemon`, `drop_pokemon`) are leftovers from an earlier single-user/local mode. They're unused by the current multi-user API but still live in the file — worth deleting or moving into the local-mode GUI scripts (`pyGuiMain.py`/`guiTest.py`) where they belong, so a reader (or interviewer) doesn't mistake them for live code. | Maintainability |
| 5 | `api.py` | 192-217 | Public read endpoints like `/api/species/search` and `/api/species/random-feed` have no rate limiting. Fine at current scale — worth a one-line mention if it comes up in an interview as a "known gap, here's how I'd address it" answer. | Performance |

### What Looks Good
- Every route that touches user-owned data (runs, pokemon, party) goes through a `require_*_access` ownership check before reading or mutating anything — this is the right pattern and it's applied consistently.
- All SQL actually reachable from `api.py` routes uses parameterized queries (`%s` placeholders), including the `LIKE` search in `get_species_search`. No live injection surface found.
- JWT verification handles both the legacy HS256 shared-secret path and RS256/ES256 via JWKS — a sensible compatibility/rotation strategy.
- No `.env` files or secrets are committed to git history.
- Clean separation between the routing layer (`api.py`) and data-access layer (`backend.py`) — easy to explain in an interview.

### Verdict
**Request Changes** before any public deployment — items 1 and 2 in Critical Issues are quick fixes (flip `debug=True` based on an env var, delete or auth-gate the debug route) but matter. Everything else is solid, and the authorization pattern in particular is a good thing to walk an interviewer through.
