import queue
import numpy as np
from datetime import datetime, timedelta
import csv
from matplotlib import pyplot as plt
import statistics

datos = []
y1 = []
y2 = []
y3 = []
with open('./res/qApp.txt') as File:
    reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_MINIMAL)
        
    for row in reader: # iot1,11:45:07.116232,7,7,5
        if row[0] == 'iot1':
            datos.append(row[2:])
            y1.append(int(row[2]))
            y2.append(int(row[3]))
            y3.append(int(row[4]))

x = np.arange(0, len(y1)/2, 0.5)
xx = np.arange(0, len(y1)/2)

max_y = max(max(y1), max(y2), max(y3)) + 2
yy = np.arange(0, max_y, 5) # y axis and step size 5

plt.subplot(3, 1, 1)
plt.step(x, y1, "-", color='#f44336')
plt.xticks(xx)
plt.yticks(yy)
ax = plt.gca()
ax.yaxis.grid(True, linestyle='dotted')
ax.axes.xaxis.set_ticklabels([])

plt.subplot(3, 1, 2)
plt.step(x, y2, "-", color='#3f51b5')
plt.xticks(xx)
plt.ylabel('Packets')
plt.yticks(yy)
ax = plt.gca()
ax.yaxis.grid(True, linestyle='dotted')
ax.axes.xaxis.set_ticklabels([])

plt.subplot(3, 1, 3)
plt.step(x, y3, "-", color='#009688')
plt.xticks(xx)
plt.yticks(yy)
ax = plt.gca()
ax.yaxis.grid(True, linestyle='dotted')
ax.axes.xaxis.set_ticklabels([])
plt.xlabel('Time [sec]')

#plt.show()
plt.savefig('./res/cApp.png')
plt.close()

#print('Mean 1 = ' + str(statistics.mean(y1)) + ' pkts')
#print('Mean 2 = ' + str(statistics.mean(y2)) + ' pkts')
#print('Mean 3 = ' + str(statistics.mean(y3)) + ' pkts')