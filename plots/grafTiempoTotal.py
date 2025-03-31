import queue
import numpy as np
from datetime import datetime
import csv
from matplotlib import pyplot as plt

def grafTT(num_iot, num_fog, num_proc, num_cloud, num_app, iot_id, iot_serv_id, iot_serv_id_first):
    files = [] # Filename of the files with processing times
    for j in range(1,num_proc+1):
        files.append('iot' + str(iot_id) + 'proc' + str(j))
    for i in range(1,num_fog+1):
        for j in range(1,num_proc+1):
            files.append('fog' + str(i) + 'proc' + str(j)) # fog1proc1
    for i in range(1,num_cloud+1):
        files.append('Cloud' + str(j)) # Cloudprocj

    result = [] # [2000,07:34:35.932774,07:34:36.936595,1000], ...
    for f in files:
        with open('./res/' + f + '.txt') as File:
            reader = csv.reader(File, delimiter=',', quotechar=',',
                                quoting=csv.QUOTE_MINIMAL)
            for row in reader:
                row.append(f)
                if row[3] != '0': 
                    result.append(row)

    result.sort()

    t_ini = []
    f = 'iotServicesGen'
    with open('./res/' + f + '.txt') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                                quoting=csv.QUOTE_MINIMAL)
        for row in reader:
            if row[2] == 'iot' + str(iot_id):
                t_ini.append(row[1]) # Time when the service is generated


    ## Total time plot

    def to_seconds(t):
        x = datetime.strptime(t,"%H:%M:%S.%f") - datetime(1900,1,1)
        #print('----------------- ' + str(x.total_seconds()))
        return x.total_seconds()

    # result[i] = ['3098', '07:27:57:273216', '07:27:57:673654', '400', 'iot1proc1']
    t0 = to_seconds(t_ini[0]) # Tiempo inicio procesado
    i = 0
    t_fin = 0 # Tiempo fin procesado
    t_total = 0 # t_fin - t0
    dic = {} # service dictionary: size/t_total

    # print(f'result = {result}')
    filtered_result = [row for row in result if row[0].startswith(str(iot_serv_id_first)[:2]) and iot_serv_id_first <= int(row[0]) <= iot_serv_id_first+999]
    # print(f'filtered_result = {filtered_result}')
    for r in filtered_result:
        try:
            t0 = to_seconds(t_ini[int(r[0]) - int(iot_serv_id_first)])
        except:
            break
        t_fin = to_seconds(r[2])
        t_total = (t_fin - t0)*1000 # Calculate processed time in ms
        dic.update({r[0]: t_total})

    x1 = []
    y1 = []

    for k in dic:
            x1.append(k)
            y1.append(dic[k]*1)

    max_y = max(y1) * 1.2

    plt.figure()
    plt.plot(x1,y1, "o", color='#f44336')
    plt.ylim([0, max_y])
    ax = plt.gca()
    ax.axes.xaxis.set_ticklabels([])
    ax = plt.gca()
    ax.yaxis.grid(True, linestyle='dotted')

    #plt.show()
    plt.title(f'Services {iot_serv_id_first} to {iot_serv_id_first + dic.__len__()}')
    plt.savefig(f'./res/tTotal_{iot_serv_id}.png')
    plt.close()

    return y1