if __name__ == '__main__':
    #file handler
    trainers = []
    tdict = {}
    tclasses= []
    with (open('bulk_raw_trainers', 'r') as file):
        tclass = ''
        tname = ''
        items = ''
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
                items = None
                # trainers.append(trainer)
            if '.trainerName' in line and line != '.trainerName=_(""),':
                #name found
                tname = line.split(')')[0].split('(')[1].replace('"','')
            if '.trainerClass' in line:
                #class found
                tclass = line.split('=')[1].replace(',','')

            if '.items' in line and line != '.items={},':
                #items found
                items = line.split('}')[0].split('{')[1].replace(' ','')

            if line == '},':
                #trainer end
                if trainer in tdict:
                    pass
                tdict[trainer] = {'trainer_class' : tclass, 'trainer_name' : tname, 'trainer_items' : items}

            trainers.append(line)

    print('done')

import sqlite3

conn = sqlite3.connect('identifier.sqlite')
cur = conn.cursor()

for i in tdict:
    pass
    package = tdict[i]
    conn.execute(
        """
        INSERT OR REPLACE INTO trainer_pool (encounter_name, trainer_name, trainer_class, trainer_items) VALUES (?, ?, ?, ?);
        """,
        (i, package['trainer_name'], package['trainer_class'], package['trainer_items']),
    )
    conn.commit()