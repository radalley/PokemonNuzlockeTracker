



#this is the mioan file for running the pokemon nuzlocke tracker

#upon launch
import sqlite3
import time
import uuid

conn = sqlite3.connect('identifier.sqlite')
cur = conn.cursor()

state = {'active_run_id' : None, 'active_attempt_id': None}

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
    # print('Please Choose by entering its Game Id:\n=========================================')
    # print('Game ID | Name')
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

def quit():
    exit

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
        new_attempt(state)
    else:
        state['active_attempt_id'] = attempts[-1][0]

    #load older attempt

    #view total pokemon

def attempt():
    pass

screens = ("screen_menu","screen_new_game","screen_load_game")

def show_screen(tag_to_show: str):
    for tag in screens:
        if dpg.does_item_exist(tag):
            dpg.hide_item(tag)
    dpg.show_item(tag_to_show)
    dpg.set_primary_window(tag_to_show, True)

def new_game_open():
    show_screen("screen_new_game")

def load_game_open():
    show_screen("screen_load_game")

#TO BE TESTED
def populate_games_combo():
    games = get_games()
    # Build display strings but store IDs
    items = [f'{g[0]} | Pokemon {g[1]} (Gen {g[3]})' for g in games]
    # Map display -> id
    mapping = {items[i]: str(games[i][0]) for i in range(len(games))}
    return items, mapping

GAME_DISPLAY_TO_ID = {}

def cb_game_selected(sender, app_data):
    # app_data is the selected display string
    dpg.set_value("newrun_game_id", GAME_DISPLAY_TO_ID.get(app_data, ""))

def cb_create_run():
    game_id = dpg.get_value("newrun_game_id")
    run_name = dpg.get_value("newrun_run_name").strip()

    if not game_id:
        dpg.set_value("newrun_status", "Pick a game.")
        return
    if not run_name:
        dpg.set_value("newrun_status", "Enter a run name.")
        return

    created_id = cur.execute('SELECT run_id FROM runs ORDER BY run_id DESC LIMIT 1').fetchone()
    created_id = 1 if not created_id else created_id[0] + 1

    cur.execute(
        "INSERT INTO runs (run_id, game_id, name, created_at) VALUES (?,?,?,?)",
        (created_id, int(game_id), run_name, time.strftime('%m-%d-%Y at %I:%M %p', time.localtime()))
    )
    conn.commit()

    state["active_run_id"] = created_id
    dpg.set_value("newrun_status", f"Created run_id={created_id}. (Next: go to Attempt screen)")
    # show_screen("attempt_screen")  # later

import dearpygui.dearpygui as dpg

dpg.create_context()

with dpg.window(tag="screen_menu", label = 'Main Menu', width=350, height=200):
    dpg.add_text("Welcome to the Dalley Pokemon Nuzlocke Tracker")
    dpg.add_button(label="New Run", callback= new_game_open)
    dpg.add_button(label='Load Run', callback= load_game_open)
    dpg.add_button(label="Quit", callback = quit)

with dpg.window(tag='screen_new_game', label = 'New Game', show=False):
    #TO BE TESTED
    dpg.add_text("Create a new run")
    game_items, GAME_DISPLAY_TO_ID = populate_games_combo()

    dpg.add_combo(
        game_items,
        label="Game",
        callback=cb_game_selected,
        width=400
    )
    # hidden value we actually store (game_id)
    dpg.add_input_text(tag="newrun_game_id", label="Selected Game ID", readonly=True, width=100)

    dpg.add_input_text(tag="newrun_run_name", label="Run Name", width=400)
    dpg.add_button(label="Create", callback=cb_create_run)
    dpg.add_text("", tag="newrun_status")
    dpg.add_button(label="Back", callback=lambda: show_screen("screen_menu"))
    #TO BE TESTED

with dpg.window(tag='screen_load_game', label = 'Load Game', show=False):
    dpg.add_text("Select run to load")

dpg.create_viewport(title='Dalley Nuzlocke Tracker', width=600, height=200)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.show_style_editor()
dpg.set_primary_window("screen_menu", True)
dpg.start_dearpygui()
dpg.destroy_context()
