# Lockley System Review & Fix Plan — 2026-07-27

Full re-review of the system against the June 30 docs (`code-review-backend.md`, `load-time-analysis.md`, `fix-proposal-hot-path.md`, `testing-strategy.md`, `ADR-001`). Every claim below was verified against the working tree today — nothing is carried forward on faith from the old docs.

**Headline:** most of the June 30 findings are already fixed — but the fixes are sitting uncommitted on a `uat` branch that is 20 commits ahead of `main`. The biggest weakness of the system today is no longer any single piece of code; it's that **the deploy/branch/repo state is unverifiable**: an empty Procfile, no CI, a stale `main`, ~1,300 lines of uncommitted work (including the performance fixes), and a Backend folder where 40+ one-off ETL scripts sit beside the two live API files.

---

## 1. What got fixed since June 30 (verified today)

| June 30 finding | Status now | Evidence |
|---|---|---|
| `_ensure_*_schema` ran ~10 queries on every request | ✅ Fixed | `_schema_ready` memoization flags, `backend.py:69` |
| `get_runs()` N+1 (300+ queries for 10 runs) | ✅ Fixed | `get_party_for_attempts_bulk` / `get_attempt_session_stats_bulk`, single query + `IN (...)` batching — **uncommitted** |
| No connection pooling | ✅ Fixed | `psycopg2.pool.ThreadedConnectionPool(1, 10)` in `api.py` — **uncommitted** |
| No route-based code splitting | ✅ Fixed | All 9 pages use `React.lazy()` in `App.jsx` |
| No `loading="lazy"` on sprites | ✅ Fixed | `Sprite.jsx:16`, `PokemonCard.jsx:189`, `PokemonFeed.jsx:276` |
| 48.5MB stray .exe in `public/sprites/types/` | ✅ Deleted from working tree | still in git history (pack is 63MB — see §2.8) |
| No test infrastructure at all | ✅ Fixed | Backend: pytest + pgserver, **33 passing** (auth, core mutations, runs listing). Frontend: vitest, **20 passing** (guestStorage). Both verified green today. |
| Admin surface | ✅ Gated | `require_admin()` checks `account_type == 'admin'`, applied to all `/api/admin/*` routes |
| Secrets hygiene | ✅ OK | `.env` untracked, `.env.example` present for both apps |

Also landed since June 30: run continuation + badge tracking, auth-schema deadlock fix, and a working Gen 5 (B/W + B2/W2) trainer extraction pipeline reading directly from NDS ROMs to preview CSVs (`build_blackwhite_trainer_preview.py` etc.).

---

## 2. Open weaknesses, ranked

### P0 — you cannot prove what production is running

**2.1 The performance fixes are uncommitted.** Connection pooling and the `get_runs` batching — the two biggest wins from the fix proposal — exist only in the working tree (~1,320 lines modified across 16 files, uncommitted). One `git checkout .` or disk failure loses them. Nothing deployed can include them until they're committed and pushed.

**2.2 `main` is 20 commits behind `uat`, 0 ahead.** `main` is stale. Whichever branch Render/Vercel actually deploy from, half the repo's history isn't where a reader (or a rollback) expects it.

**2.3 The Procfile is empty.** This was flagged in ADR-001 (June 30) and is still empty. There is no `render.yaml` either. The production start command lives only in the Render dashboard — unreproducible, and `if __name__ == '__main__': app.run(debug=True)` (`api.py:751`) means anyone who runs the file directly gets the Werkzeug debugger, which is remote code execution if it ever faces the network.

**2.4 No CI.** There is no `.github/` directory. 53 passing tests exist and nothing runs them automatically. The test suites are the single best asset added since June — currently they only pay off when someone remembers to run them.

### P1 — live API surface issues (all previously flagged, still open)

**2.5 `/api/debug/trainer-items` is still unauthenticated** (`api.py:546`) and dumps raw `trainer_pool` rows to anyone. Flagged Critical on June 30; unchanged.

**2.6 CORS is still wide open**: `CORS(app, supports_credentials=True)` (`api.py:28`) with no `origins=` allowlist, on an API that reads `Authorization` headers.

**2.7 Input validation / error semantics.** Mutating routes still do raw `data['key']` on the JSON body (~10 sites, e.g. `api.py:206`, `433-464`) — malformed requests produce 500s instead of 400s. `_decode_supabase_jwt` still ends in `except Exception: return None` (`api.py:53`), so a Supabase outage is indistinguishable from a bad token in your logs. No rate limiting on public endpoints (`/api/species/search`, the feed).

**2.8 Pool has no health handling.** `ThreadedConnectionPool(1, 10)`: if Supabase drops an idle connection (it does), the next borrower gets an `OperationalError` with no retry/pre-ping; if 10 are ever exhausted, `getconn()` raises immediately → 500s. Fine today, but it's the kind of failure that shows up only in production, weeks from now.

### P2 — structure, hygiene, and the schema problem

**2.9 Backend/ is two live files buried in ~40 ETL scripts.** `api.py` + `backend.py` (the deployed app) sit beside `Load*.py`, `build_*_preview.py`, `update_*.py`, raw dump folders (`e_bulk_raw_trainers`, `*_build*_preview/`), `poke_db.sqlite`, `identifier.sqlite`, `api-dev.log`, `temp.py`, `guiTest.py`. ADR-001's action item ("move to `scripts/`/`etl/`") is 4 weeks old and untouched. This is now the largest readability/onboarding tax in the repo — and it grows with every generation added.

**2.10 Legacy single-user code with f-string SQL is still in `backend.py`.** The `state` dict and its functions (`drop_pokemon` — `delete from pokebank where pokemon_id = {pokemon_id}` at `backend.py:1676`, plus `backend.py:492`, `521`) remain. Not imported by `api.py`, so not exploitable today — but still one accidental import away, and it's been "one import away" for a month.

**2.11 Schema management is runtime DDL, and it has already caused an incident.** The `_ensure_*_schema` functions do `CREATE TABLE/INDEX IF NOT EXISTS` at request time; commit `1fbb100 "Prevent auth schema deadlocks"` is direct evidence this design produced production deadlocks (multiple workers racing DDL). `Backend/migrations/` exists with exactly one file. The schema's source of truth is effectively "whatever Supabase currently has."

**2.12 Tracked junk + repo weight.** `staged-files.txt` (416KB) at the root, `seed_cache/` JSONs and `identifier.sqlite` tracked (they predate their `.gitignore` rules — ignore rules don't untrack files), the deleted .exe still inflating history to a 63MB pack. ROM paths in build scripts are absolute paths into a personal OneDrive, and `psql.exe` is hardcoded — the Gen 5 pipeline only runs on this one machine.

**2.13 The README is the public face and it's wrong.** Says the backend is "Flask, FastAPI" (it's Flask only), doesn't mention Gen 5 support in flight, lists badges/run-continuation as future work (they shipped), has no dev-setup or test instructions, and doesn't link to `docs/`. For a portfolio project, the README is the first thing an interviewer reads.

### P3 — depth

**2.14 Frontend test coverage is one file** (`guestStorage`). Nothing on `AuthContext`, `Attempt`, `Box`, or `utils/api.js` error paths — the testing-strategy doc's P3 items are still open.

**2.15 `backend.py` is a 2,230-line monolith / `api.py` 45 routes in one file.** Blueprint split (ADR-001 item 1) still pending. Real, but cheaper to do *after* the dead code from 2.10 is deleted.

---

## 3. The plan

Ordered so every phase leaves the system strictly better and shippable. Sized as Claude Code working sessions (with Pro Max capacity, phases 1–3 are comfortably a weekend).

### Phase 0 — Preserve and ship what's already done *(do first, ~1 short session)*

1. **Commit the working tree** in logical chunks: (a) pooling + bulk `get_runs` backend perf work, (b) frontend component/style changes, (c) Gen 5 build scripts + sprites, (d) test configs. Nothing else in this plan matters if this work is lost.
2. **Merge `uat` → `main`** (or explicitly document that `uat` is the deploy branch and `main` is frozen — pick one; recommendation: main = production truth, uat = staging).
3. Delete `Backend/api-dev.log`, `api-dev-error.log`; `git rm --cached staged-files.txt identifier.sqlite seed_cache/` so the existing ignore rules actually apply.

*Done when:* `git status` is clean, `main` contains the perf fixes, deployed UAT still works.

### Phase 1 — Make the deploy provable *(~1 session)*

4. **Procfile**: `web: gunicorn --chdir Backend api:app --workers 2 --timeout 60` (match whatever the Render dashboard says today, then make the dashboard use the repo). Change `api.py`'s `__main__` block to `app.run(debug=os.environ.get('FLASK_DEBUG') == '1')`.
5. **Delete or gate `/api/debug/trainer-items`** behind `require_admin()`. (It also calls `.fetchall()` on `conn.execute` via the wrapper — if it's dead, delete it.)
6. **CORS allowlist**: `CORS(app, supports_credentials=True, origins=[<vercel prod url>, <uat url>, 'http://localhost:5174'])`, driven by an env var.
7. **GitHub Actions**: one workflow, two jobs — `pytest` (Backend, with pgserver) and `vitest run` + `npm run lint` + `vite build` (Frontend) — on every push/PR. Badge in the README.

*Done when:* a fresh clone + `Procfile` + env vars reproduces production; CI is green on `main`.

### Phase 2 — Cut the dead weight *(~1 session)*

8. **Delete the legacy single-user code** from `backend.py`: the `state` dict, `set_active_run`, `new_attempt`, `add_pokemon`, `drop_pokemon` (the f-string SQL, `backend.py:1671-1677`), `get_attempts` at `492`, `521`, `527`, and `guiTest.py`/`pyGuiMain.py` if unused. The June review called these "one import away from exploitable" — deletion is cheaper than vigilance. Tests must stay green.
9. **Restructure Backend/**: live app stays at `Backend/` (`api.py`, `backend.py`, `tests/`, `migrations/`, requirements); everything else moves to `Backend/etl/<gen>/` (build scripts, loaders, updaters) and `Backend/etl/output/` (preview folders, raw dumps — gitignored, they're regenerable). Parameterize ROM/psql paths via env vars or a small `etl/config.py` so the pipeline is runnable anywhere.
10. **(Optional, when convenient)** history rewrite with `git filter-repo` to drop the .exe blob (63MB → ~15MB pack). Coordinate with the two remotes; low urgency, do it before sharing the repo widely.

*Done when:* `ls Backend/` shows <15 entries; grep for f-string SQL returns only parameterized `IN (...)` placeholder builds.

### Phase 3 — Harden the request path *(~1 session)*

11. **`validate_required(data, [...])` helper** returning 400 with a field list; apply to the ~10 raw `data['key']` routes.
12. **Log before swallowing** in `_decode_supabase_jwt` (`app.logger.warning` with exception class) so auth outages are diagnosable.
13. **Pool resilience**: wrap `getconn` use so an `OperationalError` on first use discards the connection and retries once (or move to the Supabase pooled connection string / PgBouncer port and keep the app pool small). Add `maxconn` sizing note next to the gunicorn worker count so they're changed together.
14. **Rate limiting** on the public read endpoints — `flask-limiter` with a per-IP default is one dependency and ~5 lines.
15. **Schema decision (ADR-002)**: freeze the `_ensure_*` functions (they stay as no-op-after-first-run guards), and adopt plain SQL migration files in `Backend/migrations/` as the forward path — numbered files, applied manually or via a tiny runner. Runtime DDL already caused one deadlock incident; stop growing it. Snapshot the current Supabase schema (`pg_dump --schema-only`) into the repo as `migrations/000_baseline.sql` so the schema is finally in version control.

*Done when:* malformed POSTs return 400s; schema source of truth is in the repo.

### Phase 4 — Spec & docs refresh *(~1 session)*

16. **Rewrite the README**: correct stack (Flask, not FastAPI), current feature list (badges, run continuation, Gen 1–5 trainer support status table), dev setup (backend + frontend + test commands), CI badge, link to `docs/`. Keep the Nuzlocke explainer and screenshots — they're good.
17. **Document the ROM ETL pipeline** (`docs/etl-pipeline.md`): inputs (which ROMs/decompilations per gen), the build→preview→validate→load flow the `build_*` / `load_*` scripts implement, and how `version_group_id`/`LOAD_BUILD` versioning works. This is the most impressive and least-documented engineering in the project — it's currently only in your head.
18. **Refresh `lockley-dashboard-plan.md`** backlog: close everything Phase 0–3 completes, add Gen 5 completion tasks.

### Phase 5 — Depth (ongoing, interleave with feature work)

19. Frontend tests next: `utils/api.js` error paths, `AuthContext`, one interaction test on `Attempt.jsx` (per the existing testing-strategy doc, which remains correct).
20. Blueprint split of `api.py`/`backend.py` by domain (runs/attempts, encounters, trainers, admin) — do it after §8's deletions, when files are at their smallest.
21. Product roadmap resumes: finish Gen 5 load (B/W previews → Postgres, then B2/W2), then movesets viewer, career stats page, Genlocke — per README roadmap.

---

## 4. What I'd explicitly *not* do

- **No FastAPI/ORM rewrite** — ADR-001's reasoning still holds; the perf problems were fixed inside Flask.
- **No Kubernetes/microservices/Redis** — Render + Vercel + Supabase remains the right scale.
- **No E2E suite yet** — CI on the existing 53 tests first; Playwright is a later luxury.
- **No premature sprite-CDN work** — lazy loading fixed the real problem; 25MB of sprites served per-image is fine.
