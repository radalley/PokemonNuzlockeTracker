
#this is the main file for running the pokemon nuzlocke tracker

#upon launch
import sqlite3
import time
import uuid

conn = sqlite3.connect('identifier.sqlite')
cur = conn.cursor()

state = {'active_run_id' : None, 'active_attempt_id': None}

def app():
    #start state is empty
    while True:
        if state['active_attempt_id']:
            attempt()
        elif state['active_run_id']:
            run()
        else:
            home()
    pass #new additon

def get_games():
    games = cur.execute(f'SELECT game_id, name, game_tag, generation from games where valid_game = "valid"').fetchall()
    return games

def new_game():
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

def run():
    #load current attempt
    attempts = cur.execute(f'select attempt_id, attempt_number, is_active from attempts where run_id = {state["active_run_id"]}').fetchall()
    if len(attempts) == 0:
        new_attempt()
    else:
        state['active_attempt_id'] = attempts[-1][0]

    #load older attempt

    #view total pokemon

def attempt():
    pass

def home():
    print("""
                Welcome to the Pokemon Nuzlocke Tracker
                ~ this project is created by Riley Dalley and is a WIP ~

                Please choose how you would like to proceed:

                1) New Nuzlocke
                2) Load Nuzlocke

                3) Save data and close application\n
            """)
    choice = input("> ").strip().lower()
    if choice in {'3','exit','q','quit'}:
        #exit and save
        raise SystemExit
    elif choice == '1':
        new_game()
    elif choice == '2':
        load_game()
    else:
        print('Invalid entry')

app()

#ask for new game or load game

#new game = present available games, a run will then be created based of that, games table will be used
    #uuid will be created for the given run, and attempt 1 will be created within

#load game = load runs table and allow the user to load the assosicated run
    #default will load the latest attempt


#on an attempt
    #display party, box, graveyard
    #display the script for the game, showing routes and trainers along the way

'''
    route 1
    encounter | nickname | status | shiny?]\

    route 2
    encounter | nickname | status | shiny?

    viridian forest | nickname | status | shiny?

    pewter city
    trainer brock - team - compare stats - level cap

    route 3
    encounter | nickname | status | shiny?
'''

#party
#displays the 6 available Pokémon
#one must always be present for a battle

#pokebank
#display all Pokémon with status captured

#graveyard
#display all Pokémon with status dead
