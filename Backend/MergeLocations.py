
import sqlite3

conn = sqlite3.connect('identifier.sqlite')
cur = conn.cursor()


def get_routes():
    games = cur.execute('SELECT location_name, location_id from locations').fetchall()
    available = [i[0] for i in games]
    return available
def get_encounters():
    cases = cur.execute('SELECT species_id, location_id, game_id from encounter_pool where game_id = 10').fetchall()
    available = [{'Species': i[0], 'Location_id': i[1], 'Game_id': i[2] } for i in cases]
    return available

cases = get_encounters()
sql_locs = get_routes()
# for i in kanto_locs:
#     conn.execute(
#         "INSERT OR IGNORE INTO canon_locations_frlg (canonical_name) VALUES (?);",
#         (i)
#     )
#     conn.execute(
#         """
#         INSERT OR REPLACE INTO canon_locations_frlg (canonical_name) VALUES (?);)
#         VALUES (?);
#         """,
#         (i),
#     )
print('why??????????????')
sql = "INSERT or IGNORE into canon_locations_frlg (canonical_name) VALUES (?)"
kanto_locs = ['Starter','Pallet Town','Route 1','Viridian City','Route 22','Route 2','Viridian Forest','Route 3','Route 4','Mt. Moon','Cerulean City','Route 24','Route 25','Route 5','Route 6','Vermillion City','Route 11','Digletts Cave','Route 9','Route 10','Rock Tunnel','Pokemon Tower','Route 12','Route 8','Route 7','Celadon City','Saffron City','Boss Giovanni - Silph Co','Route 16','Route 17','Route 18','Fuschia City','Safari Zone','Route 15','Route 14','Route 13','Power Plant','Route 19','Route 20','Seafoam Islands','Cinnabar Island','Pokemon Mansion','One Island','Two Island','Three Island','Route 21','Route 23','Victory Road','Foud Island','Five Island','Six Island','Seven Island','Cerulean Cave']
adjusted = [(i,) for i in kanto_locs]
cur.executemany(sql, adjusted)

conn.commit()






print('done')
