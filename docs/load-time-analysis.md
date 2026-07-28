# Lockley Load-Time Analysis

Analysis only — nothing in the codebase was changed. Findings are ranked roughly by impact, with the fix effort noted so you can pick targets.

## Biggest wins, in order

1. **`_ensure_badge_schema` runs on nearly every request** (backend) — by far the largest issue.
2. **`get_runs()` is N+1, and each iteration pays the cost above** (backend) — compounds #1.
3. **No route-based code splitting on the frontend** — every page's JS ships on first load.
4. **A 48.5MB stray file is sitting in `Frontend/public/sprites/types/`** — bloats every deploy.
5. **No connection pooling** — every API request opens a fresh Postgres connection.
6. **Sprites load eagerly with no `loading="lazy"`** — grid-heavy pages (Box, the home feed) fire off many simultaneous image requests.

## Backend

### `_ensure_badge_schema` runs on the hot path, repeatedly, per request

`_ensure_badge_schema` (`backend.py`) is meant to be one-time schema bootstrapping — it checks for tables/columns/constraints via `information_schema` lookups, creates indexes `if not exists`, and runs a guarded one-time data migration. The problem: it's called directly inside data-access functions instead of once at app startup, including `get_party_for_attempt`, `get_pokebank_feed_for_user`, `get_attempt_session_stats`-adjacent paths, and others — at least 12 call sites in the current file. Each call does roughly 8-10 extra round trips to Postgres (two `_has_constraint` checks, three-plus `_has_column` checks, four `create index if not exists` statements, one migration-applied check) before the function gets to the query you actually wanted.

Since none of that ever changes after the first successful run, this is pure repeated overhead on every request to any endpoint that touches party/badge data — which is most of the app.

**Fix shape (not applied):** run schema bootstrapping (`_ensure_auth_schema`, `_ensure_badge_schema`, `_ensure_bonus_locations_schema`, `_ensure_contact_reports_schema`) once at process startup, or gate each behind a module-level flag/cache so it only executes its checks once per process lifetime instead of once per request.

### `get_runs()` is N+1 — and it's the runs list page

For every run returned, `get_runs()` separately calls `get_party_for_attempt` (which carries the `_ensure_badge_schema` cost above, plus a query with three `LEFT JOIN LATERAL` subqueries for stat/type/ability patching), `get_attempt_session_stats`, an attempt-id lookup, and a badge-id lookup. For a user with 10 runs, that's roughly 10 × (5-6 queries each carrying ~10 schema-check queries) — well over 100 round trips to render a single "your runs" screen, which is very likely the first authenticated page a user sees after logging in.

**Fix shape (not applied):** batch these into one or two queries across all run IDs at once (e.g. a single party query with `WHERE attempt_id IN (...)` instead of one call per run), and fixing the `_ensure_badge_schema` issue above removes most of the multiplier on its own.

### No connection pooling

`get_db()` (`api.py`) opens a brand-new `psycopg2.connect()` on every Flask request via the `g` context, with no pool (no `psycopg2.pool`, no PgBouncer mentioned in the Render config). Each fresh connection means a new TCP handshake plus Postgres auth round trip before any query runs — for a Render-hosted Flask app talking to Supabase's Postgres, that's real, consistent per-request latency that pooling would eliminate.

**Fix shape (not applied):** a small connection pool (`psycopg2.pool.SimpleConnectionPool` or similar) shared across requests, or rely on Supabase's built-in connection pooler (PgBouncer) if not already using its pooled connection string.

### Index coverage is hard to verify, worth a direct check

The codebase creates indexes on `runs.user_id`, `users.email`, `users.supabase_id`, and the badge join tables — but nothing in the code creates indexes on `attempts.run_id`, `party.attempt_id`, or `pokebank.run_id`/`attempt_id`, which are filtered on constantly. Since the schema lives in Supabase and isn't version-controlled in the repo (see ADR-001's action items), I can't confirm from the code alone whether those exist. Worth running `EXPLAIN ANALYZE` on the `get_runs`/`get_party_for_attempt` queries directly against your Supabase instance to check for sequential scans.

### Flask dev server / deploy config

Already flagged in the code review, repeating here because it's also a load-time issue, not just a security one: `app.run(debug=True)` and the empty `Procfile` mean it's not guaranteed gunicorn (with multiple workers) is what's actually serving traffic. A single-threaded dev server handles one request at a time, which shows up directly as queueing delay under any concurrent load.

## Frontend

### No route-based code splitting

`App.jsx` statically imports every page — `Home`, `NewRun`, `LoadRun`, `Guides`, `Attempt`, `Box`, `Graveyard`, `ResetPassword`, `AdminReports` — with no `React.lazy()`/`Suspense`. That means a first-time visitor loads the JS for the admin reports page and every other route before they've clicked anything, all bundled into one payload by Vite.

**Fix shape (not applied):** convert the page imports in `App.jsx` to `React.lazy(() => import('./pages/...'))` wrapped in a `Suspense` boundary — a small, mechanical change given the routes are already cleanly separated by page.

### A 48.5MB file that doesn't belong

`Frontend/public/sprites/types/amd-software-adrenalin-edition-26.3.1-minimalsetup-260317_web.exe` — an AMD GPU driver installer, almost certainly dropped into the wrong folder by accident. Nothing in the app code references it, so it won't be downloaded by users, but it's sitting inside Vite's `public/` directory, which means it gets copied byte-for-byte into every production build. That inflates your deployed bundle, your git repo size, and your Vercel upload/build time for no reason.

**Fix shape (not applied):** delete it and add a `.exe`/binary-installer pattern to `.gitignore` so it can't happen again silently.

### Sprite images load eagerly, no lazy loading anywhere

None of the 24 `<img>` usages across the codebase (`Sprite.jsx`, `PokemonCard.jsx`, `TrainerCard.jsx`, `Box.jsx`, `PokemonFeed.jsx`, etc.) set `loading="lazy"`. On pages that render many Pokémon at once — the home feed grid, the Box page — every visible-and-off-screen sprite fires its network request immediately on mount rather than as it scrolls into view.

**Fix shape (not applied):** add `loading="lazy"` to the sprite `<img>` tags, especially in `Sprite.jsx` since it's the shared component most other places route through.

### The header logo is a 1.8MB animated GIF, loaded on every page

`SiteHeader.jsx` renders `/sprites/Lockley_Logo.gif` (1.8MB) as the site logo, and `SiteHeader` is presumably part of the layout for most/every page. Browser caching covers repeat navigations within a session, but the very first page a new visitor lands on pays the full 1.8MB tax just for the header logo before they've seen anything else — a meaningful hit to first paint / LCP. There are also two unused sibling files, `Lockley_Logo2.gif` and `Lockley_Logo3.gif` (1.2MB each), sitting in the sprites folder — worth checking if they're dead weight too.

**Fix shape (not applied):** a static PNG/WebP/SVG logo for the header (animated GIF is one of the least efficient formats for this), reserving the animated version for somewhere it's seen once (e.g. a splash/loading screen) rather than every page.

### Total static asset footprint

72MB in `Frontend/public/sprites` (which Vite copies verbatim into every build, unoptimized — Vite's `public/` folder bypasses its asset pipeline by design). Excluding the stray .exe, the real sprite weight is about 25MB across 5,587 files: 6.0MB Standard sprites, 5.3MB Shiny, 4.6MB Game Logos, 3.4MB trainers, 4.2MB combined for the three logo GIFs, 1.5MB badges. None of this is being downloaded all at once today since requests are per-image and per-page, but combined with no lazy-loading (above), pages with many Pokémon visible at once will request a lot of these simultaneously.

### No build-level optimizations configured

`vite.config.js` is minimal — just the React plugin, dev server, and proxy config. No `manualChunks`, no image-optimization plugin, no compression plugin. Given there's currently no code-splitting to chunk anyway, this isn't urgent, but worth revisiting once `React.lazy()` is in place — Vite handles the chunking automatically once dynamic `import()` exists, so this may not need explicit config at all.

## What's already fine

Dependency footprint is lean — just React, React Router, and the Supabase client, no heavy chart/date libraries dragging in extra weight. `index.html` is clean with no render-blocking third-party scripts. The home feed (`PokemonFeed.jsx`) already caps how many Pokémon it requests per page load via `DEFAULT_FEED_LIMIT`/`USER_FEED_LIMIT` rather than fetching unbounded data — good instinct, worth applying the same capping/pagination thinking to `Box.jsx`, which currently renders every Pokémon in the box at once.
