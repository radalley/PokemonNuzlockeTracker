if __name__ == '__main__':
    #file handler
    trainers = []
    tdict = {}
    tclasses= []
    with (open('fr_bulk_raw_trainers', 'r') as file):
        tclass = ''
        tname = ''
        items = ''
        tpic = ''
        for line in file:
            #cleanup lines
            line = line.replace("\n", '').replace(' ','')

            if len(line) == 0:
                continue
            if line[0] == '[':
                #new trainer
                trainer = line.split(']')[0].split('[')[1]
                tclass = None
                tname = None
                titems = None
                tpic = None
                tdouble = None
                # trainers.append(trainer)
            if '.trainerName' in line and line != '.trainerName=_(""),':
                #name found
                tname = line.split(')')[0].split('(')[1].replace('"','')
            if '.trainerClass' in line:
                #class found
                tclass = line.split('=')[1].replace(',','')
            if '.trainerPic' in line:
                #class found
                tpic = line.split('=')[1].replace(',','')
            if '.doubleBattle' in line:
                # class found
                tdouble = line.split('=')[1].replace(',', '')
            if '.items' in line and line != '.items={},':
                #items found
                titems = line.split('}')[0].split('{')[1].replace(' ','')
            if line == '},':
                #trainer end
                if trainer in tdict:
                    pass
                tdict[trainer] = {'trainer_class' : tclass, 'trainer_name' : tname, 'trainer_items' : titems, 'trainer_pic' : tpic, 'trainer_double' : tdouble}
            trainers.append(line)

    print('done')

import sqlite3

conn = sqlite3.connect('identifier.sqlite')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

#config
ver = 7
load_build = 2

for i in tdict:
    pass
    package = tdict[i]
    prior = conn.execute('select * from trainer_pool where trainer_class = (?) and encounter_name = (?) and version_group_id = (?)',(package['trainer_class'], i, ver)).fetchall()
    loc = None
    rematch = None
    event = None
    if prior:
        loc = prior[0]['location_id']
        rematch = prior[0]['is_rematch']
        event = prior[0]['is_event']
    if loc:
        conn.execute(
            """
            INSERT OR REPLACE INTO trainer_pool (location_id, encounter_name, trainer_name, trainer_class, trainer_items, trainer_pic, trainer_double, version_group_id, is_rematch, is_event, load_build) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (loc, i, package['trainer_name'], package['trainer_class'], package['trainer_items'], package['trainer_pic'],
             package['trainer_double'], ver, rematch, event, load_build),
        )
    else:
        conn.execute(
        """
        INSERT OR REPLACE INTO trainer_pool (encounter_name, trainer_name, trainer_class, trainer_items, trainer_pic, trainer_double, version_group_id, load_build) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (i, package['trainer_name'], package['trainer_class'], package['trainer_items'], package['trainer_pic'], package['trainer_double'], ver, load_build),
        )
conn.commit()
print('done')