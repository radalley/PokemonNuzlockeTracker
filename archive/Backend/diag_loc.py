import sqlite3
conn = sqlite3.connect('poke_db')
conn.row_factory = sqlite3.Row

tables = [r[0] for r in conn.execute("select name from sqlite_master where type='table'").fetchall()]
print("tables:", tables)

# Check event_locations columns
cols = [r[1] for r in conn.execute("pragma table_info(event_locations)").fetchall()]
print("event_locations cols:", cols)

# Sample event_locations rows
print("event_locations sample:")
for r in conn.execute("select * from event_locations limit 3").fetchall():
    print(dict(r))

# Check what run table looks like
for t in tables:
    if 'run' in t.lower():
        cols2 = [r[1] for r in conn.execute(f"pragma table_info({t})").fetchall()]
        print(f"{t} cols:", cols2)

# Pokebank location_ids
print("pokebank sample:")
for r in conn.execute("select pokemon_id, location_id, run_id, attempt_id from pokebank limit 5").fetchall():
    print(dict(r))
