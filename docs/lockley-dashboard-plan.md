# Lockley Issue Tracker — Plan + Working Backlog

This is a stopgap tracker you can use right now. The structure is written so it can be applied directly to GitHub Issues/Projects later — labels become labels, columns become Project board columns, items become issues — no rework needed once GitHub is connected.

## Labels (apply to GitHub later)

**Type:** `bug`, `feature`, `chore`, `data`
**Area:** `frontend`, `backend`, `data-pipeline`, `infra`
**Priority:** `p1`, `p2`, `p3`

## Board columns

`Backlog` → `In Progress` → `In Review` → `Done`

## Milestones

- **Backend cleanup** — pay down the structural debt called out in ADR-001 before adding more routes
- **Render deploy hardening** — make the Render deployment reproducible
- **Planned features** — the roadmap already listed in the project README

## Backlog

### Backend cleanup (from ADR-001)
- [ ] `chore` `backend` `p2` — Split `backend.py` into Flask blueprints (encounters, trainers, attempts/runs)
- [ ] `chore` `backend` `p3` — Add Alembic for schema migrations
- [ ] `chore` `infra` `p1` — Fill in the empty `Procfile` so Render deploys are reproducible
- [ ] `chore` `data-pipeline` `p3` — Move one-off loader scripts (`Load*.py`, `temp.py`, `diag_loc.py`, `testPokemon.py`, `guiTest.py`, `pyGuiMain.py`) into a `scripts/` or `etl/` subfolder

### Planned features (from README roadmap)
- [ ] `feature` `backend` `p2` — Trainer pools across all games
- [ ] `feature` `frontend` `p2` — Add location items to grab
- [ ] `feature` `frontend` `p2` — View Pokémon movesets
- [ ] `feature` `frontend` `p3` — Rebuilt UI to match selected game visuals
- [ ] `feature` `frontend` `p3` — Career stats page across all runs
- [ ] `feature` `frontend` `p3` — Revamped death screen with logs
- [ ] `feature` `backend` `p3` — Genlocke functionality (carryover between runs)
- [ ] `data` `data-pipeline` `p3` — Trainer data for gen 4+ (currently blocked on ROM decompile availability)

## When GitHub connects

Once the connector is live, tell me and I'll create these labels, set up the Project board with the columns above, and turn each backlog line into a real issue with the right labels and milestone attached.
