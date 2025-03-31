import queue
import numpy as np
from datetime import datetime, timedelta
import csv
from matplotlib import pyplot as plt
import statistics
import re
import shutil

num_proc = 1
num_app = 1

color = ["#f44336", "#3f51b5", "#009688", "#ff9800"]

def clean_csv(file):
    file_path="./res/"+file
    backup_path = file_path + "_backup"
    shutil.copy(file_path, backup_path)  # Create a backup
    
    pattern = re.compile(r'^fog\d+,\d{2}:\d{2}:\d{2}\.\d{6},\d+$')

    with open(file_path, 'r', encoding='utf-8', errors='replace') as infile:
        lines = [line.replace('\0', '').strip() for line in infile if pattern.match(line.replace('\0', '').strip())]
    
    with open(file_path, 'w', encoding='utf-8') as outfile:
        outfile.write('\n'.join(lines) + '\n')

def grafQ(n, num, title):
    datos = []
    with open("./res/" + n) as File:
        reader = csv.reader(
            File, delimiter=",", quotechar=",", quoting=csv.QUOTE_MINIMAL
        )
        next(reader)
        for row in reader:  # iot1,08:31:36.933141,5,5,2,2
            datos.append(float(row[2]))
    if datos:
        plt.plot(datos)
        plt.xlabel("Slot")
        plt.ylabel(title)
        ax = plt.gca()
        ax.yaxis.grid(True, linestyle="dotted")
        ax.axes.xaxis.set_ticklabels([])
        plt.ylim(bottom=0)
        plt.savefig("./res/" + title + ".png")
        plt.close()


def grafQIoT(filename, num, title):
    datos = {}

    with open(f"./res/{filename}") as File:
        for line in File:
            parts = line.strip().split(",")
            device = parts[0].split("iot")[1]
            q = parts[2]

            if device not in datos:
                datos[device] = []

            datos[device].append(q)

    for device, q_values in datos.items():
        plt.plot(range(len(q_values)), q_values, label=f"Device {device}") 

        plt.xlabel("Slot")
        plt.ylabel(title)
        ax = plt.gca()
        ax.yaxis.grid(True, linestyle="dotted")
        ax.axes.xaxis.set_ticklabels([])

        plt.tight_layout()
        plt.ylim(bottom=0)
        plt.savefig(f"./res/{title}{device}.png")
        plt.close()


# grafQIoT('iotQProc.txt', 1,'iot')
# grafQ('fogQProc.txt', 1, 'fog')
# grafQ('G_lyapunov.txt', 1, 'G')
