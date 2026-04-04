import sqlite3
import time

#from MergeLocations import get_encounters

# conn = sqlite3.connect('identifier.sqlite')
# cur = conn.cursor()
# conn.row_factory = sqlite3.Row

state = {'active_run_id' : None, 'active_attempt_id': None, 'active_game_id': None, 'active_starter': None, 'pool_game_id': None}
active_party = {
    1:'',
    2:'',
    3:'',
    4:'',
    5:'',
    6:''
}

def get_games(conn):
    games = conn.execute(f'SELECT game_id, name, game_tag, generation from games where valid_game = "valid"').fetchall()
    return games

def set_active_game(conn, game):
    state['active_game_id'] = game
    state['pool_game_id'] = conn.execute('select pool_game_id from games where game_id = (?)', (game,)).fetchone()['pool_game_id']

def create_run(conn, name):
    conn.execute("insert into runs (game_id, name) values (?,?)",
                (state['active_game_id'], name)
                )
    conn.commit()
    #get latest run and set
    set_active_run(conn.execute('select run_id from runs order by run_id desc limit 1').fetchone()['run_id'])

def get_runs(conn):
    return conn.execute('select runs.run_id, runs.game_id, games.name, runs.name as run_name, runs.created_at from runs left join games on runs.game_id = games.game_id order by run_id').fetchall()

def get_run_by_id(conn, run_id):
    # return conn.execute('select run_id, runs.name, runs.game_id, games.name as game_name from runs left join games on runs.game_id = games.game_id where runs.run_id = (?)',(run_id,)).fetchone()
    return conn.execute('select run.run_id, run.name, run.game_id, run.game_name, attempts.starter from (select run_id, runs.name, runs.game_id, games.name as game_name from runs left join games on runs.game_id = games.game_id where runs.run_id = (?)) as run left join attempts on run.run_id = attempts.run_id order by attempts.attempt_id desc limit 1',(1,)).fetchone()

def set_active_run(run_id):
    state['active_run_id'] = run_id

def new_attempt(conn, ):
    attempts = conn.execute(f'select attempt_number, is_active from attempts where run_id = {state["active_run_id"]}').fetchall()
    if len(attempts) == 0:
        #create new attempt on run with id = 1
        conn.execute("insert into attempts (run_id, attempt_number) values (?,?)",
                    (state['active_run_id'], 1) )
        state['active_attempt_id'] = 1
    else:
        new_attempt_number = attempts[::-1][0][0] + 1
        #create new attempt on run with id = 1
        conn.execute("insert into attempts (run_id, attempt_number, starter) values (?,?,?)",
                    (state['active_run_id'], new_attempt_number, 'Fire') )
        set_active_attempt(new_attempt_number)
    conn.commit()

def get_attempts(conn):
    return conn.execute(f'select attempt_number from attempts where run_id = {state["active_run_id"]}').fetchall()

def get_latest_attempt(conn):
    return conn.execute(f'select attempt_id from attempts where run_id = {state["active_run_id"]} order by attempt_id desc limit 1').fetchone()

def set_active_attempt(attempt):
    state['active_attempt_id'] = attempt

def get_pokebank(conn):
    return conn.execute(f'select pokemon_id, species_id, location_id, level_met, nickname, status, shiny, storage, party_slot, bonus_location, bonus_note from pokebank').fetchall()

def get_graveyard(conn):
    return conn.execute(f'select pokemon_id, species_id, location_id, level_met, nickname, status, shiny, storage, party_slot, bonus_location, bonus_note from pokebank where status = "Dead"').fetchall()

def get_party(conn):
    party = conn.execute('select party_slot, pokemon_id from party where attempt_id = (?)', (state['active_attempt_id'],)).fetchall()
    #emplace in active_party
    for member in party:
        active_party[member['party_slot']] = member['pokemon_id']

def update_party():
    pass

def swap_party_slots(pokemon_1, pokemon_2):
    active_party[pokemon_1['party_slot']] = pokemon_2['pokemon_id']
    #within party
    if pokemon_2['party_slot']:
        active_party[pokemon_2['party_slot']] = pokemon_1['pokemon_id']
    #outside of party

def drop_from_party(party_slot):
    active_party[party_slot] = ''
    update_party()

def get_box(conn):
    return conn.execute(f'select pokemon_id, species_id, location_id, level_met, nickname, status, shiny, storage, party_slot, bonus_location, bonus_note from pokebank where attempt_id = (?) and run_id = (?) and status = "Captured"', (state['active_attempt_id'], state['active_run_id'],)).fetchall()

def get_species_search(conn, name):
    return conn.execute('select name, species_id from species where name like (?)',('%'+name+'%',)).fetchall()

def add_pokemon(conn, species_id, location_id, nickname, status, shiny):
    conn.execute('insert into pokebank (run_id, attempt_id, species_id, location_id, nickname, status, shiny) values (?,?,?,?,?,?,?)', (state['active_run_id'],state['active_attempt_id'],species_id, location_id, nickname, status, shiny))
    conn.commit()

def drop_pokemon(conn, pokemon_id):
    conn.execute(f'delete from pokebank where pokemon_id = {pokemon_id}')
    conn.commit()

def get_pokemon_name_from_id(conn, species_id):
    return conn.execute('select name from species where species_id = (?)',(species_id,)).fetchone()[0]

# update_pokemon()
def get_script(conn, starter):
    return conn.execute('select trainer_id as event_id, encounter_title as display_name, sort_order, event_type from event_bosses where starter = (?) or starter is null or starter = "" '
                        'union ' +
                        'select canonical_location_id as event_id, canonical_name as display_name, sort_order, event_type from event_locations order by sort_order asc',
        (starter,)).fetchall()
    return conn.execute('select trainer_id as event_id, sort_order, event_type from event_bosses where starter = (?) or starter is null or starter = "" union select canonical_location_id as event_id, sort_order, event_type from event_locations order by sort_order asc', (state['active_starter'],)).fetchall()

def get_location_by_id(conn, location_id):
    return conn.execute('select canonical_name from event_locations where canonical_location_id = (?) and game_id = (?)', (location_id,state['pool_game_id'],)).fetchone()[0]

def get_encounter_pool(conn, location_id, game_id):
    # tmp = conn.execute('select species_id from encounter_pool left join species on encounter_ where canonical_location_id = (?) and game_id = (?)', (location_id, game_id)).fetchall()
    tmp = conn.execute('select encounter_pool.species_id, species.name from encounter_pool left join species on encounter_pool.species_id = species.species_id where canonical_location_id = (?) and game_id = (?)', (location_id, game_id)).fetchall()
    return [dict(x) for x in tmp]

def get_encounters_for_attempt(conn, run_id, attempt_id):
    return conn.execute('select species_id, location_id from pokebank where run_id = (?) and attempt_id = (?)', (run_id, attempt_id)).fetchall()

def get_trainers_by_location(conn, location_id):
    return conn.execute('Select trainer_id, encounter_name as trainer_name, location_id, is_event from trainer_pool where location_id = (?)', (location_id,)).fetchall()

def update_starter(conn, run_id, attempt_id, starter):
    conn.execute('update attempts set starter = (?) where run_id = (?) and attempt_id = (?) ',(starter, run_id,attempt_id))
    conn.commit()

def get_trainer_parties_by_encounter(conn, trainer_name):
    return conn.execute('Select species_name, iv, lvl, moves from trainer_pokemon where encounter_name = (?)', (trainer_name,)).fetchall()

if __name__ == '__main__':
    conn = sqlite3.connect('identifier.sqlite')
    conn.row_factory = sqlite3.Row

    runs = get_runs(conn)
    state['active_run_id'] = 1
    m_species_id = 1
    m_location_id = 8
    m_nickname = 'Arbithor'
    m_status = 'Captured'
    m_shiny = 'False'
    state['active_attempt_id'] = 2
    starter = 'Grass'
    set_active_game(conn, 10)

    script = [dict(x) for x in get_script(conn, starter)]
    trainers = [dict(x) for x in get_trainers_by_location(conn, m_location_id)]
    trainer_party = [dict(x) for x in get_trainer_parties_by_encounter(conn, trainers[0]['trainer_name'])]
    graveyard = get_graveyard(conn)
    pokebank = get_pokebank(conn)
    # encounter_pool = [dict(x) for x in get_encounter_pool(script[15]['event_id'])]
    # encounter_pool_names = [get_pokemon_name_from_id(x['species_id']) for x in encounter_pool]
    location_dict = {}
    for event in script:
        if event['event_type'] == 'Location':
            location_dict[f'Location: {get_location_by_id(conn, event["event_id"])}'] = set([get_pokemon_name_from_id(conn, x['species_id']) for x in get_encounter_pool(conn, event['event_id'], 10)])
    box = get_box(conn)
    get_party(conn)
    print(f'party = {active_party}')
    swap_party_slots(  {'party_slot': 1, 'pokemon_id': active_party[1]}, {'party_slot': 4, 'pokemon_id': active_party[4]} )
    print(f'party = {active_party}')
    swap_party_slots( {'party_slot': 2, 'pokemon_id': active_party[2]}, {'party_slot': '', 'pokemon_id': 26} )
    print(f'party = {active_party}')
    run = get_run_by_id(conn,1)
    species = get_species_search(conn, 'ew')
    get_latest_attempt(conn)
