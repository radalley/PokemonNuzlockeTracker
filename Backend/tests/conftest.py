import os
import sys

# Make sure SUPABASE_URL / DATABASE_URL are at least present (even if fake) so
# importing api.py doesn't blow up on missing env handling, and so the JWKS
# fallback path in _decode_supabase_jwt fails fast instead of hanging on a
# real network call during tests.
os.environ.setdefault("SUPABASE_URL", "https://example-test-project.supabase.co")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import api as api_module


@pytest.fixture
def app():
    api_module.app.config.update(TESTING=True)
    return api_module.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def hs256_secret(monkeypatch):
    """Sets a known HS256 secret so tests can mint their own valid Supabase-style JWTs."""
    secret = "test-supabase-jwt-secret"
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    return secret


# ---------------------------------------------------------------------------
# Real-Postgres fixtures for Priority 2 integration tests.
#
# These spin up a throwaway local Postgres instance (via the `pgserver`
# package) rather than mocking psycopg2 -- the project's logic leans on raw
# SQL, so mocking the DB layer would barely test anything real. The schema
# below is a minimal reconstruction (from the queries in backend.py) of the
# tables these specific functions touch -- it is NOT the production schema
# (which lives in Supabase and isn't checked into the repo; see the
# tech-debt note about adding a schema.sql). If the real schema drifts from
# this, these tests should be updated to match.
# ---------------------------------------------------------------------------

import pgserver
import psycopg2

import backend as backend_module

SCHEMA_SQL = """
create table games (
    game_id serial primary key,
    name text,
    game_tag text,
    generation integer,
    version_group_id integer,
    valid_game text default 'valid',
    pool_game_id integer
);

create table runs (
    run_id serial primary key,
    game_id integer,
    name text,
    user_id integer,
    created_at timestamp with time zone default current_timestamp,
    victory text,
    beaten_at timestamp with time zone
);

create table attempts (
    attempt_id serial primary key,
    run_id integer,
    attempt_number integer,
    starter text
);

create table party (
    attempt_id integer,
    party_slot integer,
    pokemon_id integer
);

create table pokebank (
    pokemon_id serial primary key,
    run_id integer,
    attempt_id integer,
    species_id integer,
    canonical_location_id integer,
    nickname text,
    nature text,
    status text,
    shiny boolean,
    bonus_location integer default 0,
    gender text,
    level_met integer
);

create table canon_locations (
    canonical_location_id integer primary key,
    canonical_location_name text
);

create table event_locations (
    canonical_location_id integer,
    version_group_id integer,
    sort_order integer,
    secondary_sort_order integer,
    event_type text
);

create table species (
    species_id integer primary key,
    name text
);

create table species_stats (
    species_id integer,
    generation integer,
    bst integer,
    hp integer,
    atk integer,
    def integer,
    spa integer,
    spd integer,
    spe integer
);

create table species_types (
    species_id integer,
    generation integer,
    type1 text,
    type2 text
);

create table species_abilities (
    species_id integer,
    generation integer,
    ability1 text,
    ability2 text,
    ability3 text
);

create table trainers_defeated (
    run_id integer,
    attempt_id integer,
    trainer_id integer
);

create table event_bosses (
    event_id serial primary key,
    trainer_id integer,
    version_group_id integer,
    encounter_title text
);

create table trainer_pool (
    trainer_id serial primary key,
    encounter_name text,
    trainer_name text,
    trainer_class text,
    canonical_location_id integer,
    is_rematch text,
    is_event text,
    trainer_items text,
    trainer_pic text,
    trainer_double text,
    details text,
    version_group_id integer,
    load_build integer,
    game_id integer
);

create table trainer_pokemon (
    pk_id serial primary key,
    encounter_name text,
    species_name text,
    lvl integer,
    moves text,
    held_item text,
    iv integer,
    version_group_id integer,
    load_build integer,
    trainer_id integer,
    slot integer,
    ability text,
    ability_clean text,
    nature text
);

create table moves (
    move_id integer,
    move_name text,
    type text,
    damage_class text,
    power integer,
    accuracy integer,
    version_group_id integer
);

create table movesets (
    species_id integer,
    move_id integer,
    learn_method text,
    learn_level integer,
    version_group_id integer
);
"""

TABLES = [
    "party", "pokebank", "bonus_locations", "attempts", "runs",
    "event_locations", "canon_locations", "games",
    "species", "species_stats", "species_types", "species_abilities", "trainers_defeated",
    "event_bosses", "trainer_pool", "trainer_pokemon", "moves", "movesets",
]


@pytest.fixture(scope="session")
def pg_server(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("pgdata")
    server = pgserver.get_server(str(data_dir))
    yield server
    server.cleanup()


@pytest.fixture(scope="session")
def pg_uri(pg_server):
    return pg_server.get_uri()


@pytest.fixture(scope="session")
def _schema_initialized(pg_uri):
    raw = psycopg2.connect(pg_uri)
    cur = raw.cursor()
    cur.execute(SCHEMA_SQL)
    raw.commit()
    cur.close()
    raw.close()
    return True


@pytest.fixture
def db_conn(pg_uri, _schema_initialized):
    """A fresh PGConn-wrapped connection with all relevant tables truncated."""
    raw = psycopg2.connect(pg_uri)
    conn = backend_module.wrap_conn(raw)
    cur = raw.cursor()
    # bonus_locations is created lazily by _ensure_bonus_locations_schema, so
    # only truncate it if it already exists.
    cur.execute("select to_regclass('public.bonus_locations') is not null")
    has_bonus_table = cur.fetchone()[0]
    tables_to_clear = [t for t in TABLES if t != "bonus_locations" or has_bonus_table]
    for badge_table in ("attempt_badges", "pokemon_badges", "badges", "schema_migrations"):
        cur.execute(f"select to_regclass('public.{badge_table}') is not null")
        if cur.fetchone()[0]:
            tables_to_clear.append(badge_table)
    cur.execute(f"truncate table {', '.join(tables_to_clear)} restart identity cascade")
    raw.commit()
    cur.close()
    yield conn
    conn.close()
