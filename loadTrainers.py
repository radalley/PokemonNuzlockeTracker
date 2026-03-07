if __name__ == '__main__':
    #file handler
    trainers = []
    with open('bulk_raw_trainers', 'r') as file:
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
                tclass = ''
                tclass = ''
                # trainers.append(trainer)
            if '.trainerName' in line:
                #class found
                tclass = line.split(')')[0].split('(')[0].replace('"','')
            if '.items' in line:
                items = line.split('}')[0].split('{')[0].replace(' ','').split(',')
            if line == '},':
                #trainer end
                pass

            trainers.append(line)


    print('done')


