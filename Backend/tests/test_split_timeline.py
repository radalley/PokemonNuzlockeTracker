from pathlib import Path

import pytest

import api
import backend
import split_timeline as splits


@pytest.fixture
def seeded(db_conn):
    conn = db_conn
    # Real SQL migration, including a second application proving idempotence.
    migration = (Path(__file__).parents[1] / 'migrations/20260917_split_timeline.sql').read_text()
    conn.execute(migration)
    conn.execute(migration)
    conn.execute("insert into games(game_id, name, version_group_id) values (1001,'Blaze Black',1001), (17,'Black',11)")
    run = conn.execute("insert into runs(game_id, name) values (1001,'Test') returning run_id").fetchone()['run_id']
    attempt = conn.execute("insert into attempts(run_id, attempt_number, starter) values (%s,1,'Grass') returning attempt_id", (run,)).fetchone()['attempt_id']
    conn.execute("insert into species(species_id, name) values (495,'Snivy'),(496,'Servine')")
    mon = conn.execute("insert into pokebank(run_id,attempt_id,species_id,nickname,status,shiny,gender) values (%s,%s,495,'Leaf','Captured',true,'female') returning pokemon_id", (run, attempt)).fetchone()['pokemon_id']
    conn.execute('insert into party(attempt_id,party_slot,pokemon_id) values (%s,1,%s)', (attempt, mon))
    trainer = conn.execute("insert into trainer_pool(encounter_name,trainer_name,version_group_id) values ('BB_CHILI','CHILI',1001) returning trainer_id").fetchone()['trainer_id']
    event = conn.execute("insert into event_bosses(trainer_id,version_group_id,encounter_title,event_type,sort_order,type_focus) values (%s,1001,'Striaton','gym leader','1','Fire') returning event_id", (trainer,)).fetchone()['event_id']
    conn.commit()
    return conn, run, attempt, mon, trainer, event


def test_snapshot_survives_evolution_and_repeated_win(seeded):
    c, run, attempt, mon, trainer, event = seeded
    assert backend.mark_trainer_victory(c, run, 1, trainer, event, [mon], [])['success']
    c.execute('update pokebank set species_id=496, nickname=\'New name\' where pokemon_id=%s', (mon,))
    c.commit()
    assert backend.mark_trainer_victory(c, run, 1, trainer, event, [mon], [mon])['success']
    records = splits.get_records(c, attempt)
    assert len(records) == 1
    assert records[0]['party'][0]['species_id'] == 495
    assert records[0]['party'][0]['nickname'] == 'Leaf'
    assert records[0]['party'][0]['shiny'] is True
    assert records[0]['party'][0]['gender'] == 'female'
    assert records[0]['party'][0]['died_in_battle'] is False
    assert c.execute('select status from pokebank where pokemon_id=%s', (mon,)).fetchone()['status'] == 'Captured'


def test_fallen_participant_kept_even_if_removed_from_party(seeded):
    c, run, attempt, mon, trainer, event = seeded
    c.execute('delete from party where pokemon_id=%s', (mon,))
    c.commit()
    assert backend.mark_trainer_victory(c, run, 1, trainer, event, [mon], [mon])['success']
    member = splits.get_records(c, attempt)[0]['party'][0]
    assert member['died_in_battle'] and member['available']
    assert c.execute('select status from pokebank where pokemon_id=%s', (mon,)).fetchone()['status'] == 'Dead'
    c.execute('delete from pokebank where pokemon_id=%s', (mon,))
    c.commit()
    assert splits.get_records(c, attempt)[0]['party'][0]['available'] is False


def test_foreign_members_and_invalid_fainted_ids_cannot_record_win(seeded):
    c, run, attempt, mon, trainer, event = seeded
    for party, dead in [([mon + 100], []), ([mon], [mon + 100]), ([mon, mon], []), ('bad', [])]:
        result = backend.mark_trainer_victory(c, run, 1, trainer, event, party, dead)
        assert not result['success']
        c.rollback()
    assert not splits.get_records(c, attempt)
    assert not c.execute('select * from trainers_defeated').fetchall()


def test_items_game_scoped_and_survive_event_replacement(seeded):
    c, _, _, _, trainer, event = seeded
    item = splits.save_item(c, 1001, 'boss:BB_CHILI', 'Sitrus Berry', 'Thief - Audino 5%')
    assert splits.save_item(c, 1001, 'boss:BB_CHILI', 'Sitrus Berry', 'Thief - Audino 5%')['item_record_id'] == item['item_record_id']
    assert splits.get_items(c, 17) == []
    c.execute('delete from event_bosses where event_id=%s', (event,))
    c.execute("insert into event_bosses(trainer_id,version_group_id,event_type,sort_order) values (%s,1001,'gym leader','1')", (trainer,))
    c.commit()
    assert splits.catalogue(c, 1001)[0]['split_key'] == 'boss:BB_CHILI'
    assert len(splits.get_items(c, 1001)) == 1
    with pytest.raises(ValueError):
        splits.save_item(c, 17, 'boss:BB_CHILI', 'Berry', 'Gift')


def test_blaze_black_item_sources_seed_at_earliest_split(seeded):
    c, *_ = seeded
    c.execute("insert into species(species_id, name) values (524, 'Roggenrola')")
    c.commit()
    migration = (Path(__file__).parents[1] / 'migrations/20260923_blazeblack_split_item_sources.sql').read_text()
    c.execute(migration)
    c.execute(migration)
    items = splits.get_items(c, 1001)
    lenora = [item for item in items if item['split_key'] == 'badge:34']
    burgh = [item for item in items if item['split_key'] == 'badge:35']
    assert len(lenora) == 68
    assert len(burgh) == 5
    everstone = next(item for item in lenora if item['item_name'] == 'Everstone')
    assert {source['method_kind'] for source in everstone['sources']} == {'thief', 'dust_cloud'}
    assert any(source['species_name'] == 'Roggenrola' and source['chance_percent'] == 50 for source in everstone['sources'])
    assert next(item for item in lenora if item['item_name'] == 'Colbur Berry')['sources'][0]['method_kind'] == 'conditional'
    assert {item['item_name'] for item in burgh} == {'Kebia Berry', "King's Rock", 'Mental Herb', 'Occa Berry', 'Rindo Berry'}
    assert c.execute("select count(*) n from schema_migrations where migration_name='blazeblack_split_item_sources_v1'").fetchone()['n'] == 1


def test_catalogue_league_without_event_type_and_no_item_writes(seeded):
    c, *_ = seeded
    for i, title in enumerate(['Elite Four - W', 'Elite Four - E', 'Elite Four - NW', 'Elite Four - NE', 'Champion']):
        trainer = c.execute('insert into trainer_pool(encounter_name,version_group_id) values (%s,1001) returning trainer_id', (f'LEAGUE_{i}',)).fetchone()['trainer_id']
        c.execute('insert into event_bosses(trainer_id,version_group_id,encounter_title,sort_order) values (%s,1001,%s,%s)', (trainer, title, str(i + 2)))
    c.commit()
    catalogue = splits.catalogue(c, 1001, 'Grass')
    assert len(catalogue) == 6
    assert [s['kind'] for s in catalogue[1:]] == ['elite_four'] * 4 + ['champion']
    with pytest.raises(ValueError):
        splits.save_item(c, 1001, 'boss:LEAGUE_0', 'Berry', 'Gift')


def test_old_win_is_not_backfilled_from_current_party(seeded):
    c, run, attempt, mon, trainer, event = seeded
    c.execute('insert into trainers_defeated(run_id,attempt_id,trainer_id) values (%s,%s,%s)', (run, attempt, trainer))
    c.commit()
    assert backend.mark_trainer_victory(c, run, 1, trainer, event, [mon], [])['success']
    assert splits.get_records(c, attempt) == []


def test_admin_writes_require_admin(client, monkeypatch):
    monkeypatch.setattr(api, 'get_current_user', lambda: None)
    assert client.post('/api/admin/split-items', json={}).status_code == 401
    monkeypatch.setattr(api, 'get_current_user', lambda: {'user_id': 1, 'account_type': 'user'})
    for method in ('post', 'patch', 'delete'):
        assert getattr(client, method)('/api/admin/split-items', json={}).status_code == 403


def test_records_are_owner_scoped(client, monkeypatch, seeded):
    c, run, *_ = seeded
    monkeypatch.setattr(api, 'get_db', lambda: c)
    monkeypatch.setattr(api, 'get_current_user', lambda: {'user_id': 999})
    assert client.get(f'/api/runs/{run}/attempts/1/battle-records').status_code == 404
