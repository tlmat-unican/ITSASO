##  Autor: Neco Villegas Saiz
##  Universidad de Cantabria    
##  Fecha: 15/09/2022

import queue
import numpy as np
from datetime import datetime, timedelta
import csv
from matplotlib import pyplot as plt
import pandas as pd

def grafU(num_proc, node_name):
    colors = ['#009688', '#009688', '#009688', '#009688', '#3f51b5', '#3f51b5']

    # Read ioT Assigment file
    df = pd.read_csv('./res/iotAssigment.txt', delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # Count the number of times "local" appears
    iot_count = df.iloc[:, 2].str.contains('local').sum()
    print(f"Local: {iot_count} services")

    # Count the number of times "fog" appears
    fog_count = df.iloc[:, 2].str.contains('fog').sum()
    print(f"Fog: {fog_count} services")

    # Count the number of times "cloud" appears
    cloud_count = df.iloc[:, 2].str.contains('cloud').sum()
    print(f"Cloud: {cloud_count} services")

    plt.bar(0, iot_count/(iot_count+fog_count+cloud_count), label='IoT', color=colors[0])
    plt.bar(1, fog_count/(iot_count+fog_count+cloud_count), label='Fog', color=colors[1])
    plt.bar(2, cloud_count/(iot_count+fog_count+cloud_count), label='Cloud', color=colors[2])

    plt.xticks(ticks=np.arange(3), labels=['Local', 'Fog', 'Cloud'])

    plt.ylabel('Utilization [%]')
    plt.xlabel('Processing Point')

    #plt.show()
    plt.savefig('./res/' + node_name + 'Utilizacion.png')
    plt.close()