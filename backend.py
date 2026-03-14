import sqlite3
import time

conn = sqlite3.connect('identifier.sqlite')
cur = conn.cursor()
conn.row_factory = sqlite3.Row
state = {'active_run_id' : None, 'active_attempt_id': None, 'active_game_id': ''}

# games

# get_games()
def get_games():
    games = conn.execute(f'SELECT game_id, name, game_tag, generation from games where valid_game = "valid"').fetchall()
    return games

def set_active_game(game):
    state['active_game_id'] = game

# Runs

def create_run(name):
    cur.execute("insert into runs (game_id, name) values (?,?)",
                (state['active_game_id'], name)
                )
    conn.commit()
    #get latest run and set
    set_active_run(conn.execute('select run_id from runs order by run_id desc limit 1').fetchone()['run_id'])

def get_runs():
    return conn.execute('select run_id, game_id, name, created_at from runs order by run_id').fetchall()

def set_active_run(run_id):
    state['active_run_id'] = run_id

# Attempts

# create_attempt()
def new_attempt():
    attempts = cur.execute(f'select attempt_number, is_active from attempts where run_id = {state["active_run_id"]}').fetchall()
    if len(attempts) == 0:
        #create new attempt on run with id = 1
        cur.execute("insert into attempts (run_id, attempt_number) values (?,?)",
                    (state['active_run_id'], 1) )
        state['active_attempt_id'] = 1
    else:
        new_attempt_number = attempts[::-1][0][0] + 1
        #create new attempt on run with id = 1
        cur.execute("insert into attempts (run_id, attempt_number) values (?,?)",
                    (state['active_run_id'], new_attempt_number) )
        set_active_attempt(new_attempt_number)
    conn.commit()

def get_attempts():
    return conn.execute(f'select attempt_number from attempts where run_id = {state["active_run_id"]}').fetchall()

def get_latest_attempt():
    return conn.execute(f'select attempt_id from attempts where run_id = {state["active_run_id"]} order by attempt_id desc limit 1').fetchone()

def set_active_attempt(attempt):
    state['active_attempt_id'] = attempt

# Pokebank

# get_pokebank()
def get_pokebank():
    return conn.execute(f'select pokemon_id, species_id, location_id, level_met, nickname, status, shiny, storage, party_slot, bonus_location, bonus_note from pokebank').fetchall()

def add_pokemon(species_id, location_id, nickname, status, shiny):
    conn.execute('insert into pokebank (run_id, attempt_id, species_id, location_id, nickname, status, shiny) values (?,?,?,?,?,?,?)', (state['active_run_id'],state['active_attempt_id'],species_id, location_id, nickname, status, shiny))
    conn.commit()

def drop_pokemon(pokemon_id):
    conn.execute(f'delete from pokebank where pokemon_id = {pokemon_id}')
    conn.commit()
# update_pokemon()

# Locations

# get_locations()
def get_locations():
    conn.execute()

# get_encounter_pool()
# get_trainers()

# Trainers

# get_trainer_pokemon()
if __name__ == '__main__':
    state['active_run_id'] = 1
    m_species_id = 1
    m_location_id = 3
    m_nickname = 'Arbithor'
    m_status = 'Captured'
    m_shiny = 'False'    
    state['active_run_id'] = 1
    state['active_attempt_id'] = 2
    get_latest_attempt()
