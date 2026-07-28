# ADR-001: Backend Architecture — Flask API over Supabase-hosted Postgres

**Status:** Accepted (documents the current implementation)
**Date:** 2026-06-30
**Deciders:** Riley (solo project)

## Context

Lockley needs a backend that serves Pokémon game data — species stats, movesets, evolution chains, encounter pools, trainer parties — sourced from PokeAPI/PokeBase and supplemented with data scraped from decompiled GBA ROMs, all persisted in Postgres and exposed to the React/Vite frontend. Authentication is handled by Supabase (Google OAuth), so the backend's job is to verify Supabase-issued JWTs rather than own session/auth logic itself. As a solo project, the priority is keeping the iteration loop fast and infrastructure minimal, not preparing for scale that doesn't exist yet.

A large share of the actual engineering effort so far has gone into data acquisition and normalization — the repo currently has a dozen-plus standalone scripts (`LoadLocation.py`, `LoadMovesets.py`, `LoadEvolutionChains.py`, `loadTrainers.py`, `MergeLocations.py`, etc.) for seeding and reshaping the Postgres schema, alongside the live API code (`backend.py`, `api.py`).

## Decision

Lockley's backend is a single Flask application (`backend.py` / `api.py`), talking to Postgres directly via `psycopg2` (no ORM), deployed on Render via `gunicorn`. The frontend (React + Vite) deploys separately on Vercel. Postgres and auth are both provided by Supabase; the Flask backend verifies Supabase JWTs (`PyJWT`) on incoming requests instead of re-implementing auth.

## Options Considered

### Option A: Flask + raw psycopg2 (current)

| Dimension | Assessment |
|---|---|
| Complexity | Low — minimal dependencies (Flask, Flask-Cors, gunicorn, psycopg2-binary, python-dotenv, PyJWT) |
| Cost | Free tier viable on Render |
| Scalability | Fine for current solo-project traffic |
| Team familiarity | High — most of the codebase (data-loading scripts) already uses raw psycopg2/SQL |

**Pros:** Full control over SQL, which matters given the schema's irregular shape (location alias tables, stats split by `version_group` to track cross-gen balance changes). Fastest path since the existing data pipeline is already Python + psycopg2.
**Cons:** No ORM means schema changes are hand-written SQL with no migration history. `backend.py` is already 69KB — a single file risks becoming unmanageable as routes grow.

### Option B: FastAPI + SQLAlchemy

**Pros:** Async support, automatic OpenAPI docs, Pydantic validation, Alembic migrations — useful as the stats/abilities/types-by-version_group schema grows.
**Cons:** Rewrite cost for an already-working backend; async only pays off under concurrent load Lockley doesn't have; adds a learning curve with no immediate payoff at current scale.

### Option C: Supabase Edge Functions only (no separate backend)

**Pros:** One fewer service to host; scales with Supabase; no separate Render bill.
**Cons:** Edge Functions run on Deno/TypeScript — a poor fit for the existing Python data pipeline (PokeBase, ROM decompile parsing). Would mean abandoning that tooling investment entirely.

## Trade-off Analysis

The real trade-off is control and Python-ecosystem fit (current Flask approach) versus convenience and growth-readiness (FastAPI + ORM). Because most of Lockley's hard engineering work is in data acquisition and normalization rather than request routing, staying in Python via Flask was the right call — Option C would have meant rewriting the entire data pipeline in a different language for no functional gain. Flask vs. FastAPI (Option B) is a closer call; the cost of staying on Flask is technical debt accumulating in `backend.py` and no migration tooling, which is acceptable at solo-project scale but worth revisiting if the schema keeps changing or collaborators join.

## Consequences

- **Easier:** the whole pipeline — data loading scripts and live API — stays in one language and one mental model.
- **Harder:** schema changes require hand-written SQL with no migration history; `backend.py`'s size will make it harder to onboard help or locate routes as the API surface grows.
- **Revisit:** split `backend.py` into smaller modules by feature, and consider Alembic if schema changes become frequent.

## Action Items

1. [ ] Split `backend.py` into Flask blueprints (e.g. encounters, trainers, attempts/runs) to keep route files manageable
2. [ ] Add a migrations tool (Alembic) once schema changes become frequent, to avoid manual SQL drift
3. [ ] Fill in the `Procfile` (currently empty) so the Render deployment is reproducible
4. [ ] Move one-off data loading/scraping scripts (`Load*.py`, `temp.py`, `diag_loc.py`, `testPokemon.py`, `guiTest.py`, `pyGuiMain.py`) into a `scripts/` or `etl/` subfolder, separate from the live API code
