import sqlite3

conn = sqlite3.connect('identifier.sqlite')
cur = conn.cursor()

tSql = cur.execute(f'select encounter_name from trainer_pool').fetchall()
import re
a1 = True

ver = 6
load_build = 3

if a1:
    #file handler
    raw = []
    trainers = []
    tdict = {}
    lines = []
    with (open('e_bulk_raw_trainer_parties', 'r') as file):
        tclass = ''
        tname = ''
        items = ''
        active = True

        # .iv = 0,
        # .lvl = 26,
        # .species = SPECIES_MAGNETON,
        # .moves = {MOVE_SPARK, MOVE_THUNDER_WAVE, MOVE_SONIC_BOOM, MOVE_SUPERSONIC},

        iv = 0
        lvl = 0
        species = ''
        moves = ''
        held_item = ''

        for line in file:
            #cleanup lines
            oline = line
            line = line.replace("\n", '').replace(' ','')
            if active:
                raw.append(line)
            if line == '//Startofactualtrainerdata':
                active = True
            #get emerald/frlg trainer
            if 'staticconststruct' in line:
                #trainer found
                trnr = 'Trainer' + line.split('sParty_')[1].split('[')[0]
                to_snake_upper = lambda s: re.sub(r'(\d+)', r'_\1', re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2',
                                                                           re.sub(r'([a-z])([A-Z])', r'\1_\2',
                                                                                  s))).strip('_').upper()
                trnr = to_snake_upper(trnr)
                if (trnr,) not in tSql:
                    pass
                else:
                    trainers.append(trnr)

            #'staticconststructTrainerMonNoItemDefaultMovessParty_Sawyer1[]={'
            if 'conststruct' in line:
                #trainer found
                trnr = 'Trainer' + line.split('Party_')[1].split('[')[0]
                to_snake_upper = lambda s: re.sub(r'(\d+)', r'_\1', re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2',
                                                                           re.sub(r'([a-z])([A-Z])', r'\1_\2',
                                                                                  s))).strip('_').upper()
                trnr = to_snake_upper(trnr)
            if '.iv' in line:
                iv = int(line.split('=')[1].split(',')[0])
            elif '.lvl' in line or '.level' in line:
                lvl = int(line.split('=')[1].split(',')[0])
            elif '.species' in line:
                species = line.split('_')[1].split(',')[0]
            elif line[:6] == '.moves':
                # moves = line.split('{')[1].split('}')[0]
                moves = line.replace('{','').replace('}','').split('=')[1]
            elif '.heldItem' in line:
                held_item = line.split('=')[1].split(',')[0]
                held_item = held_item if held_item != 'ITEM_NONE' else ''
            else:
                lines.append(line)

            if line == '},' or line == '}':
                #end of pokemon
                if 'MAY' in trnr.upper():
                    pass
                conn.execute(
                    """
                    INSERT OR IGNORE INTO trainer_pokemon (encounter_name, species_name, iv, lvl, moves, held_item, version_group_id, load_build) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (trnr, species, iv, lvl, moves, held_item, ver, load_build),
                )

                iv = 0
                lvl = 0
                species = ''
                moves = ''
                held_item = ''

        conn.commit()


            # if line == '};':
            #     #end of trainer
            #     iv = ''
            #     lvl = 0
            #     species = ''
            #     moves = ''

a2 = False
#check for missing trainers
if a2:
    tSql = cur.execute(f'select encounter_name from trainer_pool').fetchall()
    # tSql = cur.execute(f'select encounter_name from trainer_pokemon left join trainer_pool on trainer_pokemon.enocunter_name = trainer_pool.encounter_name where trainer_pool.location_id is null').fetchall()
    # tSql = cur.execute(f'select trainer_pool.encounter_name from trainer_pokemon left join trainer_pool on trainer_pokemon.encounter_name = trainer_pool.encounter_name where trainer_pool.location_id is null').fetchall()
print("done")