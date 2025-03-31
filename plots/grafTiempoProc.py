# FIXME it only works for 3 apps or less

import queue
import numpy as np
from datetime import datetime
import csv
from matplotlib import pyplot as plt

def grafTP(num_fog, num_proc, num_cloud, num_app):
    files = [] # Nombre de los ficheros con los tiempos de procesado
    for i in range(1,num_fog+1):
        for j in range(1,num_proc+1):
            files.append('iot' + str(i) + 'proc' + str(j)) # iotiprocj
    for i in range(1,num_cloud+1):
        files.append('Cloud' + str(i)) # Cloudi

    result = [] # [2000,07:34:35.932774,07:34:36.936595,1000], ...
    for f in files:
        with open('./res/' + f + '.txt') as File:
            reader = csv.reader(File, delimiter=',', quotechar=',',
                                quoting=csv.QUOTE_MINIMAL)
            for row in reader:
                row.append(f)
                result.append(row)

    result.sort()

    ## Processing time
    def to_seconds(t):
        x = datetime.strptime(t,"%H:%M:%S.%f") - datetime(1900,1,1)
        return x.total_seconds()

    # result[i] = ['3098', '07:27:57:273216', '07:27:57:673654', '400', 'iot1proc1']
    id = '1000' # Primer servicio
    size = 0 # Total service size
    t0 = 0 # Initial processed time 
    t_fin = 0 # End processed time
    t_proc = 0 # t_fin - t0
    dic = {} # sevice dictionary: size/t_proc
    for r in result:
        #print('**** id: ' + str(id))
        if r[0] == id:
            if t0 == 0 or t0 > to_seconds(r[1]):
                t0 = to_seconds(r[1])
            t1 = to_seconds(r[2])
            if t1 > t_fin:
                t_fin = t1
            size += int(r[3])
            t_proc = t_fin - t0 # Calculate processed time
        else:
            if t_proc == 0: # The service has not been processed
                #pass
                dic.update({id: 0})
            else:
                dic.update({id: size/t_proc})
            id = r[0]
            size = int(r[3])
            t0 = to_seconds(r[1])
            t_fin = to_seconds(r[2])
            t_proc = t_fin - t0 # Calculate processed time (no fragmentation)

        #print('id: ' + str(id) + ', t_proc: ' + str(t_proc) + ', size: ' + str(size) + ', t0: ' + str(t0) + ', t_fin: ' + str(t_fin))

    x1 = []
    y1 = []
    x2 = []
    y2 = []
    x3 = []
    y3 = []
    for k in dic:
        if int(k) < 2000: # App 1
            x1.append(k)
            y1.append(dic[k]*1)

        elif int(k) < 3000: # App 2
            x2.append(k)
            y2.append(dic[k]*1)

        else: # App 3
            x3.append(k)
            y3.append(dic[k]*1)

    if not x2:
        max_y = max(y1) * 1.2
    elif not x3:
        max_y = max(max(y1), max(y2)) * 1.2
        '''min_x = min(len(x1), len(x2))
        x1 = x1[0:min_x]
        y1 = y1[0:min_x]
        x2 = x2[0:min_x]
        y2 = y2[0:min_x]'''
    else:
        max_y = max(max(y1), max(y2), max(y3)) * 1.2
        '''min_x = min(len(x1), len(x2), len(x3))
        x1 = x1[0:min_x]
        y1 = y1[0:min_x]
        x2 = x2[0:min_x]
        y2 = y2[0:min_x]
        x3 = x3[0:min_x]
        y3 = y3[0:min_x]'''

    yy = np.arange(0, round(max_y,-3)+1, round(max_y,-3)/5)

    plt.subplot(num_app, 1, 1)
    plt.plot(x1,y1, "o", color='#f44336')
    plt.ylim([0, max_y])
    plt.yticks(yy)
    #plt.grid(True)
    ax = plt.gca()
    ax.axes.xaxis.set_ticklabels([])
    ax = plt.gca()
    ax.yaxis.grid(True, linestyle='dotted')

    if x2:
        plt.subplot(num_app, 1, 2)
        plt.plot(x2,y2, "o", color='#3f51b5')
        plt.ylim([0, max_y])
        plt.yticks(yy)
        plt.ylabel('bps')
        #plt.grid(True)
        ax = plt.gca()
        ax.axes.xaxis.set_ticklabels([])
        ax = plt.gca()
        ax.yaxis.grid(True, linestyle='dotted')

    if x3:
        plt.subplot(num_app, 1, 3)
        plt.plot(x3,y3, "o", color='#009688')
        plt.ylim([0, max_y])
        plt.yticks(yy)
        #plt.grid(True)
        ax = plt.gca()
        ax.axes.xaxis.set_ticklabels([])
        plt.xlabel('Services')
        ax = plt.gca()
        ax.yaxis.grid(True, linestyle='dotted')

    #plt.show()
    plt.savefig('./res/tProc.png')
    plt.close()