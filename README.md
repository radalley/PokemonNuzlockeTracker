# Lockley — Pokémon Nuzlocke Tracker

A learning project by Riley Dalley. The name blending "Nuzlocke" with my personal names.

Lockley is a full-stack web application for tracking Pokémon Nuzlocke runs. The initial target game is **FireRed / LeafGreen**. The long-term goal is a multi-user, device-agnostic platform where players can log encounters, track their party, and follow a game script showing routes and boss fights in order.

This project is being built as a deliberate learning exercise to understand *why* things are built a certain way matters as much as getting them working.

---

## Project Status

The project has a working full-stack foundation. Core seeding scripts are complete, the database schema is mostly stable, and the Flask API + React frontend can communicate. Active development is focused on solidifying the data model before any styling or deployment work.

---

## Architecture Overview

```
lockley/
├── backend.py          # All business logic and SQL queries
├── api.py              # Flask HTTP layer — thin translation only
├── identifier.sqlite   # SQLite database
│
├── loadPokemon.py      # Seeds species and gen3 stat tables from PokéAPI
├── LoadLocation.py     # Seeds encounter pool from PokéAPI (with local cache)
├── loadTrainers.py     # Parses raw FRLG trainer data into trainer_pool
├── loadTrainerPokemon.py # Parses raw FRLG party data into trainer_pokemon
├── MergeLocations.py   # Maps raw PokeAPI location IDs to canonical locations
│
└── frontend/           # React app (Vite)
    ├── pages/
    │   ├── Home.jsx
    │   ├── NewRun.jsx
    │   ├── LoadRun.jsx
    │   └── Attempt.jsx
    └── components/
        ├── LocationRow.jsx
        ├── BossRow.jsx
        └── RivalRow.jsx
```

### The Core Principle: Separation of Concerns

A strict boundary is enforced between `api.py` and `backend.py`:

- **`backend.py`** owns all SQL and business logic. Every function accepts a `conn` parameter.
- **`api.py`** only translates HTTP requests into calls to `backend.py` and formats responses. No SQL belongs here.

This mirrors a real-world pattern where your API layer and data layer are kept independent, making both easier to test and eventually swap out (e.g., replacing SQLite with PostgreSQL later).

---

## Database Schema

The database is SQLite (`identifier.sqlite`). Schema changes are managed manually.

### Core Tables

| Table | Purpose |
|---|---|
| `species` | Master list of Pokémon (National Dex ID + name) |
| `species_gen3` | Gen 3 stats, types, and abilities per species |
| `games` | All mainline games, flagged `valid_game` for UI display |
| `runs` | A named playthrough tied to a game |
| `attempts` | A single run attempt (one per life; a new attempt = a reset) |
| `pokebank` | All Pokémon caught in an attempt, with status and storage slot |

### Reference / Mapping Tables

| Table | Purpose |
|---|---|
| `locations` | Raw PokeAPI location areas with their API IDs |
| `canon_locations_frlg` | Cleaned, ordered canonical locations for FRLG's script |
| `location_alias_map_frlg` | Maps raw location IDs → canonical location IDs |
| `encounter_pool` | Which species appear at which location in which game |
| `trainer_pool` | Individual trainers with class, name, and items |
| `trainer_pokemon` | The party each trainer brings to battle |
| `evolutions_gen3` | Evolution chains (seeded but not yet used in UI) |

### Key Design Decisions

**`sort_order` on `canon_locations_frlg`**
Locations and bosses need to appear in game progression order. A float `sort_order` column makes it easy to insert new entries between existing ones (e.g., `sort_order = 4.5` slots between 4 and 5) without renumbering the whole table.

**Canonical location mapping**
PokéAPI splits locations into many fine-grained "location areas" (e.g., `mt-moon-1f`, `mt-moon-b1f`, `mt-moon-b2f`). For a Nuzlocke tracker, you only get one encounter per *location*, so these all map to a single canonical "Mt. Moon" entry via `location_alias_map_frlg`. The `match_method` column records whether a mapping was done by an exact rule or manually.

**Rival encounters and starter filtering**
The rival's team changes depending on which starter you picked. The `get_script` query filters rival encounters by the attempt's `starter` value (Fire / Water / Grass). Gym leaders and other bosses have a null/empty starter field, so they pass through regardless.

---

## Backend (`backend.py`)

### State

A global `state` dict tracks the active run, attempt, game, and starter for the current session:

```python
state = {
    'active_run_id': None,
    'active_attempt_id': None,
    'active_game_id': None,
    'active_starter': None,
    'pool_game_id': None
}
```

> **Learning note:** This global state works fine for a single-user local app. For a multi-user web app, this would need to move to session storage or a database-backed approach — one of the planned future changes.

### Per-Request Database Connections

Connections are created per HTTP request using Flask's `g` object, not shared globally:

```python
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('identifier.sqlite')
        g.db.row_factory = sqlite3.Row
    return g.db
```

**Why this matters:** SQLite connections are not thread-safe. If a single connection were shared across Flask's worker threads, you'd get `ProgrammingError: SQLite objects created in a thread can only be used in that same thread`. Using `g` ensures each request gets its own connection, which is closed when the request ends via `@app.teardown_appcontext`.

### `sqlite3.Row` vs Plain Tuples

The `conn.row_factory = sqlite3.Row` setting makes query results behave like dictionaries — you can access columns by name (`row['species_id']`) instead of by index (`row[0]`). This makes the code much more readable and less brittle when columns are reordered.

### Key Functions

| Function | What it does |
|---|---|
| `get_script(conn, starter)` | Returns the ordered game script (locations + bosses) filtered by starter type |
| `get_encounter_pool(conn, location_id, game_id)` | Returns catchable species for a location |
| `get_trainers_by_location(conn, location_id)` | Returns trainers assigned to a location |
| `get_trainer_parties_by_encounter(conn, trainer_name)` | Returns a trainer's full party |
| `get_run_by_id(conn, run_id)` | Returns run details including the most recent attempt's starter |

---

## API (`api.py`)

The Flask API is a thin HTTP wrapper. Each route gets a connection via `get_db()`, calls the appropriate `backend.py` function, and returns JSON.

| Endpoint | Method | Description |
|---|---|---|
| `/api/games` | GET | List of valid games |
| `/api/runs` | GET | All runs |
| `/api/runs/<run_id>` | GET | Single run with starter info |
| `/api/runs` | POST | Create a new run |
| `/api/script?starter=Fire` | GET | Ordered game script for a starter type |
| `/api/encounter-pool/<location_id>?game_id=X` | GET | Encounter pool for a location |
| `/api/trainer-list/<location_id>` | GET | Trainers at a location |

CORS is enabled via `flask-cors` to allow the Vite dev server (typically `localhost:5173`) to communicate with Flask (typically `localhost:5000`).

---

## Frontend (React / Vite)

The frontend uses React Router for navigation and fetches data from the Flask API.

### Pages

- **`Home`** — entry point, links to new or existing runs
- **`NewRun`** — game selection and run naming form
- **`LoadRun`** — lists existing runs to resume
- **`Attempt`** — the main tracker screen; fetches run details and the game script

### Components

- **`LocationRow`** — renders a route/area; fetches encounter pool and trainer list lazily
- **`BossRow`** — renders a gym leader or major boss encounter
- **`RivalRow`** — renders a rival fight; filtered to the correct starter variant

### Data Flow on the Attempt Screen

1. `Attempt` fetches run details (`/api/runs/<id>`) to get the game and starter.
2. It uses the starter to fetch the ordered script (`/api/script?starter=Fire`).
3. Each `LocationRow` independently fetches its encounter pool and trainer list when rendered.
4. Trainer parties are loaded eagerly when a trainer dropdown is opened, stored in a local object keyed by `trainer_name`.

---

## Seeding Scripts

The database is populated from two sources: the PokéAPI (via the `pokebase` library) and raw C source files from the FRLG decompilation project.

### PokéAPI Seeding

All API responses are cached to `seed_cache/` as JSON files so the scripts can be re-run without re-fetching.

| Script | What it seeds |
|---|---|
| `loadPokemon.py` | `species` and `species_gen3` — stats, types, abilities for Gen 1 (Dex #1–151) |
| `LoadLocation.py` | `encounter_pool` — which Pokémon appear where, per game version |

### Trainer Seeding

FRLG trainer data comes from parsing C struct definitions sourced from the game's decompilation:

| Script | What it seeds |
|---|---|
| `loadTrainers.py` | `trainer_pool` — trainer identity (name, class, items) |
| `loadTrainerPokemon.py` | `trainer_pokemon` — each trainer's party (species, level, IVs, moves) |

The parser converts PascalCase struct names (e.g., `sParty_LeaderBrock`) to `SCREAMING_SNAKE_CASE` (`TRAINER_LEADER_BROCK`) to match the trainer enum names used elsewhere.

### Location Canonicalization

`MergeLocations.py` builds the bridge between PokéAPI's granular location areas and the simplified location list a Nuzlocke tracker needs:

- `canon_locations_frlg` is the hand-curated list of locations in game order.
- `location_alias_map_frlg` maps each raw PokéAPI `location_id` to the appropriate canonical entry.
- Some edge cases (e.g., SS Anne) are folded into the nearest city for now, with the option to split later.

---

## What's Next

- **`event_bosses` and `event_locations` tables** — `backend.py` already queries these, but they need to be created and populated. These drive the ordered game script that the `Attempt` page displays.
- **`party` table** — a dedicated join table for tracking which Pokémon occupy which party slots in an attempt.
- **`attempts.starter` column** — needs to be added to the schema to match what `backend.py` expects.
- **Styling pass** — functionality comes first; CSS later.
- **Docker + PostgreSQL** — planned once the data model is stable.
- **Multi-user auth** — login system so multiple users can track runs from any device.

---

## Running Locally

```bash
# Backend
pip install flask flask-cors pokebase
python api.py

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

The Flask API runs on `http://localhost:5000` and the Vite dev server on `http://localhost:5173`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Database | SQLite |
| Backend | Python / Flask |
| Frontend | JavaScript / React (Vite) |
| API client data | PokéAPI via `pokebase` |
| Routing | React Router |
| Planned deployment | Docker |
