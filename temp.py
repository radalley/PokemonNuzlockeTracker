'''from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pkmngame.sqlite"

print("Creating DB at:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON;")

conn.execute("""
CREATE TABLE IF NOT EXISTS species (
    species_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS species_gen3 (
    species_id INTEGER PRIMARY KEY,
    type1 TEXT NOT NULL,
    type2 TEXT,
    type3 TEXT,
    FOREIGN KEY (species_id) REFERENCES species(species_id)
);
""")

conn.commit()

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print("Tables now:", tables)

conn.close()
'''

lst = [1,2,2,3,4,5,6,6,6,7,8,8]

pass