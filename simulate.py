""" This script sets up and runs `n` simulations.

It defines key parameters like simulation time, traffic rates, delay requirements,
and number of nodes. It also calls `graficas.py` for result visualization.
"""

import os
import json
import matplotlib.pyplot as plt
from plots.grafColas import grafQ,grafQIoT,clean_csv
from plots.grafUtilizacion import grafU
from plots.grafTiempoTotal import grafTT
from plots.grafBateria import grafBat, grafBat_average, grafBat_every_alg, run_out_battery
from plots.grafDecisions import grafDec
from plots.grafDecisionsOverTime import grafDecisionsOverTime
from plots.grafFailsOverTime import grafFailsOverTime,FailsOverTimeWhileBattery
from plots.grafFails import grafFails
from plots.grafBatteryvsFails import plot_battery_fails_scatter

# Clear previous results
os.system("sudo rm ./res/*")

# Load configuration from file
with open("cnf/config.json", "r") as jsonfile:
    config = json.load(jsonfile)

def clearDockers():
    os.system('sudo docker stop $(sudo docker ps -a -q)')
    os.system('sudo docker rm $(sudo docker ps -a -q)')

if config["simulation"]["mode"] == "local":
    # Cloud
    print("Deploying Cloud...")
    os.system("python3 cloudRec.py cnf/local.json 1 &")
    # Fog
    print("Deploying Fog...")
    os.system("python3 nodoFog.py cnf/local.json 1")
    # IoT
    print("Deploying IoT...")
    os.system("python3 nodoIot.py cnf/local.json 1")
else:  # docker
    os.system("sh launch.bash") # Build DockerFile
    num_iot = config["iot_nodes"]
    if num_iot == 1:
        os.system("docker compose -f test_1_device.yaml up")
    elif num_iot == 2:
        os.system("docker compose -f test_2_devices.yaml up")
    elif num_iot == 3:
        os.system("docker compose -f test_3_devices.yaml up")
    elif num_iot == 5:
        os.system("docker compose -f test_5_devices.yaml up")
    elif num_iot == 10:
        os.system("docker compose -f test_10_devices.yaml up")
    elif num_iot == 15:
        os.system("docker compose -f test_15_devices.yaml up")
    elif num_iot == 20:
        os.system("docker compose -f test_20_devices.yaml up")
    try:
        clearDockers()
    except Exception as e:
        print(f"ERROR clearing dockers: {e}")

## Results

# Utilization
num_proc_iot = config["iot1"]["num_proc"]
try:
    print("Plotting utilization...")
    grafU(num_proc_iot, "iot")
except Exception as e:
    print("ERROR plotting utilization...")

# Battery
battery = max([config[f"iot{i}"]["battery"] for i in range(1, num_iot + 1)])
try:
    print("Plotting battery...")
    grafBat("iot",num_iot,max_bat=battery)
except Exception as e:
    print("ERROR plotting battery...")
try:
    print("Plotting average battery...")
    grafBat_average("iot",num_iot,max_bat=battery)
except Exception as e:
    print("ERROR plotting average battery...") 
try:
    print("Plotting run out battery...")
    run_out_battery("iot",num_iot,filepath="res")
except Exception as e:
    print("ERROR plotting run out battery: ", e)

# Decisions
try:
    print("Plotting decisions...")
    grafDec("iot")
except Exception as e:
    print("ERROR plotting decisions: ", e)

try:
    print("Plotting decisions...")
    grafDecisionsOverTime("./res")
except Exception as e:
    print("ERROR plotting decisions over time: ", e)

# Fails
try:
    print("Plotting fails...")
    grafFails("res")
except Exception as e:
    print("ERROR plotting fails: ", e)
try:
    print("Plotting fails over time...")
    grafFailsOverTime("res")
except Exception as e:
    print("ERROR plotting fails over time: ", e)
try:
    print("Plotting fails with battery over time...")
    FailsOverTimeWhileBattery("res")
except Exception as e:
    print("ERROR plotting fails with battery over time: ", e)

# Time
num_fog = config["fog_nodes"]
num_cloud = config["cloud_nodes"]
num_app = config["simulation"]["num_app"]
num_proc_fog = config["fog1"]["num_proc"]
print('Plotting time...')
y = []
for j in range(1, num_iot+1):
    try:
        y.append(grafTT(num_iot, num_fog, num_proc_fog, num_cloud, num_app, j, j, j*1000))
    except Exception as e:
        print(f'ERROR plotting time for iot{j}: {e}')
plt.figure()
plt.boxplot(y, showmeans=True)
plt.ylabel('Time (ms)')
plt.xlabel('IoT devices')
plt.savefig(f'./res/tTotalBoxplot.png')
plt.close()

try:
    print('Plotting local processor queues...')
    grafQIoT('iotQProc.txt', num_proc_iot, 'iotQProc')
except Exception as e:
    print('ERROR plotting local processor queues: ', e)
    print(e)
try:
    print('Plotting fog processor queues...')
    grafQ('fogQProc.txt', num_proc_fog, 'fogQProc')
except Exception as e:
    print(f"ERROR plotting fog processor queues: {e}")
    try:
        print('Plotting fog processor queues...')
        clean_csv('fogQProc.txt')
        grafQ('fogQProc.txt', num_proc_fog, 'fogQProc')
    except Exception as e:
        print(f"ERROR plotting fog processor queues: {e}")  
try:
    print('Plotting cloud processor queues...')
    grafQ('cloudQProc.txt', 1, 'cloudQProc')
except:
    print('ERROR plotting cloud processor queues')