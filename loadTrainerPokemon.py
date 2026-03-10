import sqlite3

conn = sqlite3.connect('identifier.sqlite')
cur = conn.cursor()

tSql = cur.execute(f'select encounter_name from trainer_pool').fetchall()
import re
if __name__ == '__main__':
    #file handler
    raw = []
    trainers = []
    tdict = {}
    tclasses= []
    with (open('bulk_raw_trainer_parties', 'r') as file):
        tclass = ''
        tname = ''
        items = ''
        active = False

        # .iv = 0,
        # .lvl = 26,
        # .species = SPECIES_MAGNETON,
        # .moves = {MOVE_SPARK, MOVE_THUNDER_WAVE, MOVE_SONIC_BOOM, MOVE_SUPERSONIC},

        iv = ''
        lvl = 0
        species = ''
        moves = ''

        for line in file:
            #cleanup lines
            line = line.replace("\n", '').replace(' ','')
            if active:
                raw.append(line)
            if line == '//Startofactualtrainerdata':
                active = True
            if line[:17] == 'staticconststruct':
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
            if line[:3] == '.iv':
                iv = int(line.split('=')[1].split(',')[0])
            if line[:4] == '.lvl':
                lvl = int(line.split('=')[1].split(',')[0])
            if line[:8] == '.species':
                species = line.split('_')[1].split(',')[0]
            if line[:6] == '.moves':
                moves = line.split('{')[1].split('}')[0]


            if line == '},':
                #end of pokemon
                conn.execute(
                    """
                    INSERT OR REPLACE INTO trainer_pokemon (encounter_name, species_name, iv, lvl, moves) VALUES (?, ?, ?, ?, ?);
                    """,
                    (trnr, species, iv, lvl, moves),
                )

                iv = ''
                lvl = 0
                species = ''
                moves = ''
        conn.commit()


            # if line == '};':
            #     #end of trainer
            #     iv = ''
            #     lvl = 0
            #     species = ''
            #     moves = ''





print("done")