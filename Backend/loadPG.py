import sqlite3
import psycopg2

sqlite_conn = sqlite3.connect('identifier.sqlite')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()

pg_conn = psycopg2.connect(
    host="localhost",
    port = 5173,
    database="Lockley",
    user="postgres",
    password="SummerTime54!"  # whatever you set during install
)
pg_cur = pg_conn.cursor()

# get all tables from sqlite
sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in sqlite_cur.fetchall()]

TABLE_ORDER = [
    'species',
    'locations',
    'games',
    'runs',
    'attempts',
    'event_locations',
    'location_alias_map_frlg',  # depends on locations + event_locations
    'encounter_pool',
    'pokebank',                  # depends on runs + species
    'party',
    'evolutions',
    'movesets',
    'moves',
    'badges',
    'trainers_defeated',
    'trainer_pokemon',
    'species_types',
    'species_abilities',
    'species_stats',
    'event_bosses',
    'bonus_locations',
    'trainer_pool',
    'users',
]

for table in TABLE_ORDER:
    # skip internal SQLite tables
    if table.startswith('sqlite_'):
        continue
    # get data
    sqlite_cur.execute(f"SELECT * FROM {table}")
    rows = sqlite_cur.fetchall()
    if not rows:
        continue

    # get column names
    cols = [desc[0] for desc in sqlite_cur.description]
    cols_str = ', '.join(cols)
    placeholders = ', '.join(['%s'] * len(cols))

    for row in rows:
        pg_cur.execute(
            f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})",
            tuple(row)
        )

pg_conn.commit()
print("Migration complete")

# import sqlite3
#
# conn = sqlite3.connect('identifier.sqlite')
# cur = conn.cursor()
#
# cur.execute("SELECT sql FROM sqlite_master WHERE type='table'")
# for row in cur.fetchall():
#     print(row[0])
#     print(";")