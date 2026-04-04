from flask import Flask, jsonify, request, g
from flask_cors import CORS
import sqlite3
import time
from backend import (get_games, create_run, get_runs, get_script,
                     get_encounter_pool, get_run_by_id, get_trainers_by_location,
                     get_trainer_parties_by_encounter, get_species_search, update_starter)

app = Flask(__name__)
CORS(app)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('identifier.sqlite')
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route('/api/games', methods=['GET'])
def games_route():
    conn = get_db()
    games = get_games(conn)
    return jsonify([dict(g) for g in games])

@app.route('/api/runs', methods=['GET'])
def get_runs_route():
    conn = get_db()
    runs = get_runs(conn)
    return jsonify([dict(r) for r in runs])

@app.route('/api/runs/<int:run_id>', methods=['GET'])
def get_run_route(run_id):
    conn = get_db()
    run = get_run_by_id(conn, run_id)
    return jsonify(dict(run))

@app.route('/api/runs', methods=['POST'])
def runs_route():
    conn = get_db()
    data = request.get_json()
    # set state before calling create_run
    from backend import state, set_active_game
    set_active_game(conn, data['game_id'])
    create_run(conn, data['run_name'])
    return jsonify({'success': True, 'run_id': state['active_run_id']})

@app.route('/api/script', methods=['GET'])
def script_route():
    conn = get_db()
    starter = request.args.get('starter')
    if not starter:
        return jsonify([])
    script = get_script(conn, starter)
    return jsonify([dict(r) for r in script])

@app.route('/api/encounter-pool/<int:location_id>', methods=['GET'])
def encounter_pool_route(location_id):
    conn = get_db()
    game_id = request.args.get('game_id')
    pool = get_encounter_pool(conn, location_id, game_id)
    return jsonify(pool)

@app.route('/api/trainer-list/<int:location_id>', methods=['GET'])
def trainer_list_route(location_id):
    conn = get_db()
    trainers = get_trainers_by_location(conn, location_id)
    return jsonify([dict(t) for t in trainers])

@app.route('/api/trainer-party/<trainer_name>', methods=['GET'])
def trainer_party_route(trainer_name):
    conn = get_db()
    party = get_trainer_parties_by_encounter(conn, trainer_name)
    return jsonify([dict(p) for p in party])

@app.route('/api/species/search', methods=['GET'])
def species_search_route():
    conn = get_db()
    query = request.args.get('q', '')
    species = get_species_search(conn, query)
    return jsonify([dict(s) for s in species])

@app.route('/api/update-starter', methods=['POST'])
def update_starter_route():
    conn = get_db()
    data = request.get_json()
    run_id = int(data['run_id'])
    attempt_id = int(data['attempt_id'])
    starter = data['starter']
    update_starter(conn, run_id, attempt_id, starter)
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)