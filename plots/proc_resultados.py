import queue
import numpy as np
from datetime import datetime, timedelta
import csv

num_fog = 1
num_proc = 4
num_clouds = 2

files = []


for i in range(1,num_fog+1):
    for j in range(1,num_proc+1):
        files.append('Fog' + str(i) + 'proc' + str(j))

for i in range(1,num_clouds+1):
    files.append('Cloud' + str(i))

result = []

for f in files:
    with open('./res/' + f + '.txt') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_MINIMAL)
        for row in reader:
            row.append(f)
            result.append(row)

f1p1 = 0 # Number of services processed
f1p1b = 0 # b processed
f1p2 = 0
f1p2b = 0
f1p3 = 0
f1p3b = 0
f1p4 = 0
f1p4b = 0
f2p1 = 0
f2p1b = 0
f2p2 = 0
f2p2b = 0
f2p3 = 0
f2p3b = 0
f2p4 = 0
f2p4b = 0
c1 = 0
c1b = 0
c2 = 0
c2b = 0
result.sort()
for r in result:
    t_proc = datetime.strptime(r[2], "%H:%M:%S.%f") - datetime.strptime(r[1], "%H:%M:%S.%f")
    t_proc = t_proc.total_seconds()
    print('Service ' + r[0] + ' (' + r[3] + ' b) processed in ' + str(t_proc) + ' seconds at ' + r[4])
    if r[4] == 'Fog1proc1':
        f1p1 += 1
        f1p1b += int(r[3])
    elif r[4] == 'Fog1proc2':
        f1p2 += 1
        f1p2b += int(r[3])
    elif r[4] == 'Fog1proc3':
        f1p3 += 1
        f1p3b += int(r[3])
    elif r[4] == 'Fog1proc4':
        f1p4 += 1
        f1p4b += int(r[3])
    elif r[4] == 'Fog2proc1':
        f2p1 += 1
        f2p1b += int(r[3])
    elif r[4] == 'Fog2proc2':
        f2p2 += 1
        f2p2b += int(r[3])
    elif r[4] == 'Fog2proc3':
        f2p3 += 1
        f2p3b += int(r[3])
    elif r[4] == 'Fog2proc4':
        f2p4 += 1
        f2p4b += int(r[3])
    elif r[4] == 'Cloud1':
        c1 += 1
        c1b += int(r[3])
    elif r[4] == 'Cloud2':
        c2 += 1
        c2b += int(r[3])

print('\nFOG1:')
print('\t- Proc1: ' + str(f1p1) + ' services ' + str(f1p1b) + ' b')
print('\t- Proc2: ' + str(f1p2) + ' services ' + str(f1p2b) + ' b')
print('\t- Proc3: ' + str(f1p3) + ' services ' + str(f1p3b) + ' b')
print('\t- Proc4: ' + str(f1p4) + ' services ' + str(f1p4b) + ' b')

print('\nFOG2:')
print('\t- Proc1: ' + str(f2p1) + ' services ' + str(f2p1b) + ' b')
print('\t- Proc2: ' + str(f2p2) + ' services ' + str(f2p2b) + ' b')
print('\t- Proc3: ' + str(f2p3) + ' services ' + str(f2p3b) + ' b')
print('\t- Proc4: ' + str(f2p4) + ' services ' + str(f2p4b) + ' b')

print('\nCLOUD:')
print('\t- Cloud1: ' + str(c1) + ' services ' + str(c1b) + ' b')
print('\t- Cloud2: ' + str(c2) + ' services ' + str(c2b) + ' b')

t_gen = []
with open('./res/Fog_servicesGen.txt') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_MINIMAL)
        for row in reader:
            t_gen.append(row[1])

t_assigment = []
serv_cloud1 = []
with open('./res/Fog_assigment.txt') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_MINIMAL)
        for row in reader:
            t_assigment.append(row[1])
            if row[2] == 'cloud::1':
                serv_cloud1.append(row) # 1153,07:59:43:534983,cloud::1,fog2

# Calculate round-trip delay
delay = []
suma = 0
for i in range(len(t_gen)):
    delay.append((datetime.strptime(t_assigment[i], "%H:%M:%S.%f") - datetime.strptime(t_gen[i], "%H:%M:%S.%f")).total_seconds())

print('\nDelay Fog-Master-Fog ' + str(sum(delay)/len(t_gen) * 1000) + ' ms' + ' (min ' + str(min(delay)*1000) + ' ms)')

proc_cloud1 = []
with open('./res/Cloud1.txt') as File:
    reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_MINIMAL)
    for row in reader:
        proc_cloud1.append(row)


# Calculate one-way delay between Fog and Cloud1
proc_cloud1.sort()

delayy = []
suma = 0
for s in serv_cloud1:
    for p in proc_cloud1:
        if p[0] == s[0]: #mismo servID
            if datetime.strptime(p[1], "%H:%M:%S.%f") > datetime.strptime(s[1], "%H:%M:%S.%f"):
                delayy.append((datetime.strptime(p[1], "%H:%M:%S.%f") - datetime.strptime(s[1], "%H:%M:%S.%f")).total_seconds())

if len(serv_cloud1) !=0:
    print('Delay Fog-Cloud1 ' + str(sum(delayy)/len(serv_cloud1) * 1000) + ' ms' + ' (min ' + str(min(delayy)*1000) + ' ms, max ' + str(max(delayy)*1000) + ' ms)')


# Utilization
from matplotlib import pyplot as plt

datos = []
with open('./res/Utilizacion.txt') as File:
    reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_MINIMAL)
    
    i = 0
    for row in reader:
        if row[0] == 'fog1' or row[0] == 'fog2': 
            plt.bar(i, float(row[2]), label=str(row[0]+row[1]))
        else:
            plt.bar(i, float(row[1]), label=str(row[0]))
        i += 1

plt.legend(loc='upper right', ncol=3, fancybox=True, shadow=True)
plt.yticks(np.linspace(0,100,num=11))

frame1 = plt.gca()
frame1.axes.get_xaxis().set_visible(False)

plt.show()
#plt.savefig("utilizacion.png")

## Processed time plot
from datetime import datetime
def to_seconds(t):

    from datetime import datetime
    x = datetime.strptime(t,"%H:%M:%S.%f") - datetime(1900,1,1)
    #print('----------------- ' + str(x.total_seconds()))
    return x.total_seconds()

# result[i] = ['3098', '07:27:57:273216', '07:27:57:673654', '400', 'Fog1proc1']

id = '1000'
size = 0
t0 = 0
t_fin = 0
dic = {}
for r in result:
    print('**** id: ' + str(id))
    if r[0] == id:
        if t0 == 0 or t0 > to_seconds(r[1]):
            t0 = to_seconds(r[1])
        t1 = to_seconds(r[2])
        if t1 > t_fin:
            t_fin = t1
        size += int(r[3])
        t_proc = t_fin - t0 # Calculated processed time
    else:
        dic.update({id: size/t_proc})
        id = r[0]
        size = int(r[3])
        t0 = to_seconds(r[1])
        t_fin = to_seconds(r[2])
        t_proc = t_fin - t0 # Calculate processed time (no fragmentation)

    print('id: ' + str(id) + ', t_proc: ' + str(t_proc) + ', size: ' + str(size) + ', t0: ' + str(t0) + ', t_fin: ' + str(t_fin))

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

max_y = max(max(y1), max(y2), max(y3)) * 1.2
min_x = min(len(x1), len(x2), len(x3))
x1 = x1[0:min_x]
y1 = y1[0:min_x]
x2 = x2[0:min_x]
y2 = y2[0:min_x]
x3 = x3[0:min_x]
y3 = y3[0:min_x]

plt.subplot(3, 1, 1)
plt.plot(x1,y1, "o", color='#f44336')
plt.ylim([0, max_y])
#plt.yticks(np.linspace(0, max_y, num=5))
#plt.grid(True)
ax = plt.gca()
ax.axes.xaxis.set_ticklabels([])

plt.subplot(3, 1, 2)
plt.plot(x2,y2, "o", color='#3f51b5')
plt.ylim([0, max_y])
#plt.yticks(np.linspace(0, max_y, num=5))
plt.ylabel('bps')
#plt.grid(True)
ax = plt.gca()
ax.axes.xaxis.set_ticklabels([])

plt.subplot(3, 1, 3)
plt.plot(x3,y3, "o", color='#009688')
plt.ylim([0, max_y])
#plt.yticks(np.linspace(0, max_y, num=5))
#plt.grid(True)
ax = plt.gca()
ax.axes.xaxis.set_ticklabels([])
plt.xlabel('Services')

plt.show()

