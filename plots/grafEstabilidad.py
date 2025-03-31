import queue
import numpy as np
from datetime import datetime, timedelta
import csv
from matplotlib import pyplot as plt
import statistics

num_proc = 4
num_app = 3

color = ['#f44336', '#3f51b5', '#009688', '#ff9800']

def grafE(n, num, name):
    datos = []
    with open('./res/' + n) as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                                quoting=csv.QUOTE_MINIMAL)
        next(reader)
        for row in reader: # iot1,08:31:36.933141,5,5,2,2
            datos.append(float(row[2]))

    y = np.cumsum(datos, axis=0)/np.arange(1, len(datos)+1)

    plt.plot(y)
    plt.xlabel('Slot')
    plt.ylabel(name)
    ax = plt.gca()
    ax.yaxis.grid(True, linestyle='dotted')
    ax.axes.xaxis.set_ticklabels([])
    plt.savefig('./res/' + name + '.png')
    plt.close()


# for i in range(10):
#     grafE(f'G_lyapunov_iot{i+1}.txt', 1, f'G_stability iot{i+1}')