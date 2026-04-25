import os
from pathlib import Path
import jwt
from jwt import PyJWKClient
from flask import Flask, jsonify, request, g, send_from_directory, abort
from flask_cors import CORS
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import time
from backend import (get_games, create_run, get_runs, get_script,
                     get_encounter_pool, get_run_by_id, get_trainers_by_location,
                     get_trainer_parties_by_encounter, get_species_search, update_starter, delete_run,
                     get_pokebank_for_attempt, upsert_encounter, delete_encounter, get_evolutions,
                     get_evolution_families, get_attempt_page_data, get_attempts_for_run, create_attempt_for_run,
                     get_party_for_attempt, add_to_party_for_attempt, remove_from_party_for_attempt,
                     mark_trainer_victory, get_pokemon_trainers_and_badges, get_badges_by_ids,
                     get_pokebank_with_stats, get_attempt_session_stats, create_bonus_location,
                     delete_bonus_location, rename_bonus_location, get_species_summary,
                     get_or_create_user_by_supabase_id,
                     run_belongs_to_user, pokemon_belongs_to_user, wrap_conn)

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIST_DIR = BACKEND_DIR.parent / 'Frontend' / 'dist'

app = Flask(__name__, static_folder=None)

# Keep local dev easy while allowing stricter production CORS.
cors_origins_env = os.environ.get('LOCKLEY_CORS_ORIGINS', '').strip()
if cors_origins_env:
    cors_origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
else:
    cors_origins = ['http://localhost:5173', 'http://localhost:5174']

CORS(app, supports_credentials=True, origins=cors_origins)

# JWKS client for asymmetric JWT verification (cached at module level)
_jwks_client = None

def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        supabase_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
        _jwks_client = PyJWKClient(f"{supabase_url}/auth/v1/.well-known/jwks.json")
    return _jwks_client

def _decode_supabase_jwt(token):
    """Try HS256 legacy secret first, then fall back to JWKS asymmetric verification."""
    secret = os.environ.get('SUPABASE_JWT_SECRET', '')
    if secret:
        try:
            return jwt.decode(token, secret, algorithms=['HS256'], audience='authenticated')
        except jwt.PyJWTError:
            pass
    try:
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(token, signing_key.key, algorithms=['RS256', 'ES256'], audience='authenticated')
    except Exception:
        return None

def get_db():
    if 'db' not in g:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise RuntimeError('DATABASE_URL environment variable is not set')
        raw = psycopg2.connect(database_url)
        g.db = wrap_conn(raw)
    return g.db

def get_current_user():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[7:]
    payload = _decode_supabase_jwt(token)
    if not payload:
        return None
    supabase_id = payload.get('sub')
    if not supabase_id:
        return None
    email = payload.get('email')
    return get_or_create_user_by_supabase_id(get_db(), supabase_id, email=email)

def require_auth():
    user = get_current_user()
    if not user:
        return None, (jsonify({'error': 'Authentication required'}), 401)
    return user, None

def require_run_access(conn, run_id):
    user, error = require_auth()
    if error:
        return None, error
    if not run_belongs_to_user(conn, run_id, user['user_id']):
        return user, (jsonify({'error': 'Run not found'}), 404)
    return user, None

def require_pokemon_access(conn, pokemon_id):
    user, error = require_auth()
    if error:
        return None, error
    if not pokemon_belongs_to_user(conn, pokemon_id, user['user_id']):
        return user, (jsonify({'error': 'Pokemon not found'}), 404)
    return user, None

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        if error:
            db.rollback()
        db.close()

@app.route('/api/auth/me', methods=['GET'])
def auth_me_route():
    user = get_current_user()
    return jsonify({'authenticated': bool(user), 'user': user})

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout_route():
    # Token invalidation is handled client-side via Supabase SDK
    return jsonify({'success': True})

@app.route('/api/games', methods=['GET'])
def games_route():
    conn = get_db()
    games = get_games(conn)
    return jsonify([dict(g) for g in games])

@app.route('/api/runs', methods=['GET'])
def get_runs_route():
    conn = get_db()
    user, error = require_auth()
    if error:
        return error
    runs = get_runs(conn, user_id=user['user_id'])
    return jsonify([dict(r) for r in runs])

@app.route('/api/runs/<int:run_id>/<int:attempt_number>', methods=['GET'])
def get_run_route(run_id, attempt_number):
    conn = get_db()
    user, error = require_run_access(conn, run_id)
    if error:
        return error
    run = get_run_by_id(conn, run_id, attempt_number, user_id=user['user_id'])
    if run:
        return jsonify(dict(run))
    return jsonify({'error': 'Run or attempt not found'}), 404

@app.route('/api/runs', methods=['POST'])
def runs_route():
    conn = get_db()
    user, error = require_auth()
    if error:
        return error
    data = request.get_json() or {}
    # set state before calling create_run
    from backend import state, set_active_game
    set_active_game(conn, data['game_id'])
    create_run(conn, data['run_name'], user_id=user['user_id'])
    return jsonify({'success': True, 'run_id': state['active_run_id']})

@app.route('/api/script', methods=['GET'])
def script_route():
    conn = get_db()
    starter = request.args.get('starter')
    if not starter:
        return jsonify([])
    version_group_id = request.args.get('version_group_id', type=int)
    script = get_script(conn, starter, version_group_id=version_group_id)
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
    run_id = request.args.get('run_id', type=int)
    attempt_number = request.args.get('attempt_number', type=int)
    if run_id is not None:
        _, error = require_run_access(conn, run_id)
        if error:
            return error
    trainers = get_trainers_by_location(conn, location_id, run_id=run_id, attempt_number=attempt_number)
    return jsonify([dict(t) for t in trainers])

@app.route('/api/trainer-party/<trainer_name>', methods=['GET'])
def trainer_party_route(trainer_name):
    conn = get_db()
    game_id = request.args.get('game_id', type=int)
    party = get_trainer_parties_by_encounter(conn, trainer_name, game_id)
    return jsonify(party)

@app.route('/api/species/search', methods=['GET'])
def species_search_route():
    conn = get_db()
    query = request.args.get('q', '')
    species = get_species_search(conn, query)
    return jsonify([dict(s) for s in species])

@app.route('/api/species/<int:species_id>/summary', methods=['GET'])
def species_summary_route(species_id):
    conn = get_db()
    game_id = request.args.get('game_id', type=int)
    species = get_species_summary(conn, species_id, game_id=game_id)
    if not species:
        return jsonify({'error': 'Species not found'}), 404
    return jsonify(species)

@app.route('/api/evolutions/<int:species_id>', methods=['GET'])
def evolutions_route(species_id):
    conn = get_db()
    evolutions = get_evolutions(conn, species_id)
    return jsonify([dict(e) for e in evolutions])

@app.route('/api/evolution-families', methods=['GET'])
def evolution_families_route():
    conn = get_db()
    ids_param = request.args.get('ids', '')
    if not ids_param:
        return jsonify([])
    species_ids = [int(x) for x in ids_param.split(',') if x.strip().isdigit()]
    family = get_evolution_families(conn, species_ids)
    return jsonify(family)

@app.route('/api/update-starter', methods=['POST'])
def update_starter_route():
    conn = get_db()
    data = request.get_json() or {}
    run_id = int(data['run_id'])
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    attempt_number = int(data['attempt_id'])  # rename to attempt_number
    starter = data['starter']
    update_starter(conn, run_id, attempt_number, starter)
    return jsonify({'success': True})

@app.route('/api/pokebank/save', methods=['POST'])
def save_encounter_route():
    conn = get_db()
    data = request.get_json() or {}
    run_id = int(data['run_id'])
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    if data.get('pokemon_id'):
        _, pokemon_error = require_pokemon_access(conn, int(data['pokemon_id']))
        if pokemon_error:
            return pokemon_error
    pokemon_id = upsert_encounter(
        conn,
        run_id,
        int(data['attempt_number']),
        int(data['location_id']),
        int(data['species_id']),
        data.get('nickname') or None,
        data.get('nature') or None,
        data.get('status'),
        data.get('shiny'),
        int(data['pokemon_id']) if data.get('pokemon_id') else None,
        int(data.get('bonus_location') or 0)
    )
    return jsonify({'success': True, 'pokemon_id': pokemon_id})

@app.route('/api/runs/<int:run_id>/attempts/<int:attempt_number>/bonus-locations', methods=['POST'])
def create_bonus_location_route(run_id, attempt_number):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    data = request.get_json() or {}
    canonical_location_id = data.get('canonical_location_id')
    if canonical_location_id is None:
        return jsonify({'error': 'canonical_location_id required'}), 400

    result = create_bonus_location(conn, run_id, attempt_number, int(canonical_location_id))
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/runs/<int:run_id>/attempts/<int:attempt_number>/bonus-locations', methods=['DELETE'])
def delete_bonus_location_route(run_id, attempt_number):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    data = request.get_json() or {}
    canonical_location_id = data.get('canonical_location_id')
    secondary_sort_order = data.get('secondary_sort_order')
    if canonical_location_id is None or secondary_sort_order is None:
        return jsonify({'error': 'canonical_location_id and secondary_sort_order required'}), 400

    result = delete_bonus_location(conn, run_id, attempt_number, int(canonical_location_id), int(secondary_sort_order))
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/runs/<int:run_id>/attempts/<int:attempt_number>/bonus-locations', methods=['PATCH'])
def rename_bonus_location_route(run_id, attempt_number):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    data = request.get_json() or {}
    canonical_location_id = data.get('canonical_location_id')
    secondary_sort_order = data.get('secondary_sort_order')
    canonical_name = data.get('canonical_name')
    if canonical_location_id is None or secondary_sort_order is None:
        return jsonify({'error': 'canonical_location_id and secondary_sort_order required'}), 400

    result = rename_bonus_location(
        conn,
        run_id,
        attempt_number,
        int(canonical_location_id),
        int(secondary_sort_order),
        canonical_name,
    )
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/pokebank/<int:pokemon_id>', methods=['DELETE'])
def delete_encounter_route(pokemon_id):
    conn = get_db()
    _, error = require_pokemon_access(conn, pokemon_id)
    if error:
        return error
    delete_encounter(conn, pokemon_id)
    return jsonify({'success': True})

@app.route('/api/pokebank/<int:run_id>/<int:attempt_id>', methods=['GET'])
def pokebank_route(run_id, attempt_id):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    data = get_pokebank_for_attempt(conn, run_id, attempt_id)
    return jsonify(data)

@app.route('/api/debug/trainer-items', methods=['GET'])
def debug_trainer_items_route():
    conn = get_db()
    rows = conn.execute(
        "SELECT trainer_id, encounter_name, trainer_name, trainer_items "
        "FROM trainer_pool WHERE trainer_items IS NOT NULL AND trainer_items != '' LIMIT 50"
    ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/attempt-page/<int:run_id>/<int:attempt_number>', methods=['GET'])
def attempt_page_route(run_id, attempt_number):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    data = get_attempt_page_data(conn, run_id, attempt_number)
    if not data:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(data)

@app.route('/api/runs/<int:run_id>/attempts/<int:attempt_number>/session-stats', methods=['GET'])
def attempt_session_stats_route(run_id, attempt_number):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    data = get_attempt_session_stats(conn, run_id, attempt_number)
    if 'error' in data:
        return jsonify(data), 404
    return jsonify(data)

@app.route('/api/runs/<int:run_id>/attempts', methods=['GET'])
def get_attempts_route(run_id):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    attempts = get_attempts_for_run(conn, run_id)
    return jsonify([dict(a) for a in attempts])

@app.route('/api/runs/<int:run_id>/attempts', methods=['POST'])
def create_attempt_route(run_id):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    new_num = create_attempt_for_run(conn, run_id)
    return jsonify({'attempt_number': new_num})

@app.route('/api/runs/<int:run_id>/attempts/<int:attempt_number>/party', methods=['GET'])
def get_party_route(run_id, attempt_number):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    party = get_party_for_attempt(conn, run_id, attempt_number)
    return jsonify([dict(p) for p in party])

@app.route('/api/runs/<int:run_id>/attempts/<int:attempt_number>/party', methods=['POST'])
def add_to_party_route(run_id, attempt_number):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    data = request.get_json() or {}
    pokemon_id = data.get('pokemon_id')
    if not pokemon_id:
        return jsonify({'error': 'pokemon_id required'}), 400
    _, pokemon_error = require_pokemon_access(conn, int(pokemon_id))
    if pokemon_error:
        return pokemon_error
    slot = add_to_party_for_attempt(conn, run_id, attempt_number, int(pokemon_id))
    if slot is None:
        return jsonify({'error': 'Party full or attempt not found'}), 400
    return jsonify({'party_slot': slot})

@app.route('/api/runs/<int:run_id>/attempts/<int:attempt_number>/party/<int:pokemon_id>', methods=['DELETE'])
def remove_from_party_route(run_id, attempt_number, pokemon_id):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    _, pokemon_error = require_pokemon_access(conn, pokemon_id)
    if pokemon_error:
        return pokemon_error
    remove_from_party_for_attempt(conn, run_id, attempt_number, pokemon_id)
    return jsonify({'success': True})

@app.route('/api/runs/<int:run_id>/attempts/<int:attempt_number>/trainer-victory', methods=['POST'])
def trainer_victory_route(run_id, attempt_number):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    data = request.get_json() or {}
    trainer_id = data.get('trainer_id')
    if trainer_id is None:
        return jsonify({'error': 'trainer_id required'}), 400

    result = mark_trainer_victory(
        conn,
        run_id,
        attempt_number,
        int(trainer_id),
        data.get('trainer_name') or '',
        data.get('trainer_class') or '',
        data.get('encounter_title') or '',
    )
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/box/<int:run_id>/<int:attempt_number>', methods=['GET'])
def box_route(run_id, attempt_number):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    data = get_pokebank_with_stats(conn, run_id, attempt_number)
    return jsonify(data)

@app.route('/api/pokemon/<int:pokemon_id>/trainers-badges/<int:run_id>/<int:attempt_number>', methods=['GET'])
def pokemon_trainers_badges_route(pokemon_id, run_id, attempt_number):
    conn = get_db()
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    _, pokemon_error = require_pokemon_access(conn, pokemon_id)
    if pokemon_error:
        return pokemon_error
    data = get_pokemon_trainers_and_badges(conn, run_id, attempt_number, pokemon_id)
    if 'error' in data:
        return jsonify(data), 404
    return jsonify(data)

@app.route('/api/badges', methods=['GET'])
def badges_route():
    conn = get_db()
    ids_param = request.args.get('ids', '')
    if not ids_param:
        return jsonify([])

    badge_ids = [x.strip() for x in ids_param.split(',') if x.strip()]
    data = get_badges_by_ids(conn, badge_ids)
    return jsonify(data)

@app.route('/api/delete-run', methods=['POST'])
def delete_run_route():
    conn = get_db()
    data = request.get_json() or {}
    run_id = int(data['run_id'])
    _, error = require_run_access(conn, run_id)
    if error:
        return error
    delete_run(conn, run_id)
    return jsonify({'success': True})


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def frontend_route(path):
    if path.startswith('api/'):
        abort(404)

    if not FRONTEND_DIST_DIR.exists():
        return jsonify({
            'error': 'Frontend build not found',
            'hint': 'Run "npm run build" inside Frontend before starting the backend in production.'
        }), 404

    requested = (FRONTEND_DIST_DIR / path).resolve()
    if path and requested.is_file() and FRONTEND_DIST_DIR in requested.parents:
        return send_from_directory(FRONTEND_DIST_DIR, path)

    return send_from_directory(FRONTEND_DIST_DIR, 'index.html')



if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8000'))
    app.run(host='0.0.0.0', port=port, debug=True)