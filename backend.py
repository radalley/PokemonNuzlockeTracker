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

# Runs

# create_runs()
def create_run(name):
    cur.execute("INSERT into runs (game_id, name) values (?,?)",
                (state['active_game_id'], name)
                )
    state['active_run_id'] = created_id
    conn.commit()

def new_run():
    #list games
    #create run
    #for each generation
    games = get_games()
    game_dict = {}
    for i in games:
        gen = f'Generation {i[3]}'
        game_dict[gen] = game_dict.get(gen, [])
        game_dict[gen].append((i[0], i[1], i[2]))
    '''
    {'gen 1': [(1,'red'), (2, 'blue')]
    '''
    print('Please Choose by entering its Game Id:\n=========================================')
    print('Game ID | Name')
    valid_ids = []
    for key, value in game_dict.items():
        print(key)
        for item in value:
            valid_ids.append(str(item[0]))
            print(f'{item[0]} | Pokemon {item[1]}')

    while state['active_run_id'] is None:
        created_game_id = input('> ')
        if created_game_id in valid_ids:
            #create run off id
            created_id = cur.execute('select run_id from runs order by run_id desc limit 1').fetchone()
            if not created_id:
                created_id = 1
            else:
                created_id = created_id[0] + 1
            created_name = ''
            while len(created_name) == 0:
                created_name = input('Please Enter Name for Run > ')
            cur.execute("INSERT into runs (run_id, game_id, name, created_at) values (?,?,?,?)",
                (created_id, created_game_id, created_name, time.strftime(f'%m-%d-%Y at %I:%M %p', time.localtime()))
            )
            conn.commit()
            state['active_run_id'] = created_id
            #open run
        else:
            print('Invalid: Please enter game id')

#load_runs()
def load_game():
    #display runs
    runs = cur.execute('SELECT run_id, games.name, runs.name, runs.created_at from runs LEFT JOIN games on runs.run_id=games.game_id').fetchall()
    print('Please select by entering run id:')
    # print('Run ID | Name | Version | Date Created')
    print(f' \n{"ID":<3} | {"Run Name":<20} | {"Game":<10} | {"Created"}\n{"=" * 60}')
    run_ids = []
    for i in runs:
        # print(f'{i[0]:<3} | {i[2]} | {i[1]} | {i[3]}')
        run_ids.append(str(i[0]))
        print(f'{i[0]:<3} | {i[2]:<20} | {i[1]:<10} | {i[3]}')

    selection = ''
    while selection not in run_ids:
        selection = input('> ').strip().lower()

    state['active_run_id'] = int(selection)

#get_runs()

# Attempts

# create_attempt()
def new_attempt():
    attempts = cur.execute(f'select attempt_id, attempt_number, is_active from attempts where run_id = {state["active_run_id"]}').fetchall()
    if len(attempts) == 0:
        #create new attempt on run with id = 1
        cur.execute("insert into attempts (run_id, attempt_number) values (?,?)",
                    (state['active_run_id'], 1) )
        state['active_attempt_id'] = 1
    else:
        pass
    conn.commit()

# get_attempts()

# get_latest_attempt()

# Pokebank

# get_pokebank()
# add_pokemon()
# drop_pokemon()
# update_pokemon()

# Locations

# get_locations()
# get_encounter_pool()
# get_trainers()

# Trainers

# get_trainer_pokemon()
if __name__ == '__main__':
    print('hello')