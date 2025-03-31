'''
Reads all configuration from the JSON file and manages shared variables used by threads.
Import this module wherever needed.
'''

import json
import queue
import threading
import time
import sys
import numpy as np
import csv
import logging

cont_serv_success = 0

conns = {} # Store connections to other nodes

services_gen = {}  # To store information about the generated services
serv_time_results = {}  # To store information about the generated services' times

fogInfo = {}  # To store updated information about the Fog nodes

queue_lock = threading.Lock()

# Read configuration from JSON file
with open(str(sys.argv[1]), 'r') as jsonfile:
    config = json.load(jsonfile)

# Traffic control
delay = [] # En cada elemento los delays de cada nodo IoT
with open(config['simulation']['tc_iot_fog_delay'], newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for row in reader:
        delay.append(row)

# Algorithm
alg_name = config['simulation']['algorithm']

# Log
logNodoFog = config['logger']['nodoFog']
logTrafficGen = config['logger']['trafficGen']
logProcessor = config['logger']['processor']
logService = config['logger']['service']
logCloud = config['logger']['cloud']
logIot = config['logger']['iot']

traf_gen = config['simulation']['traf_gen'] # Módulo con el generador de tráfico
num_app = config['simulation']['num_app']

cont_paq = np.zeros(num_app) # Para ver cuantos paquetes se generan en trafficGen

# Delay requirements
iot_nodes = config['iot_nodes']
serv_delay_req = []
for i in range(iot_nodes):
    serv_delay_req.append(config['iot'+str(i+1)]['delay_req'])

# Delay between fog and cloud
delay_fog_cloud = config['simulation']['delay_fog_cloud']


# Addresses and ports
fog_nodes = config['fog_nodes']
fog_host = []
fog_port = []
fog_control_port = []
for i in range(fog_nodes):
    fog_host.append(config['fog' + str(i+1)]['host'])
    fog_port.append(config['fog' + str(i+1)]['port'])
    fog_control_port.append(config['fog' + str(i+1)]['control_port'])

cloud_nodes = config['cloud_nodes']
cloud_host = []
cloud_port = []
cloud_control_port = []
for i in range(cloud_nodes):
    cloud_host.append(config['cloud' + str(i+1)]['host'])
    cloud_port.append(config['cloud' + str(i+1)]['port'])
    cloud_control_port.append(config['cloud' + str(i+1)]['control_port'])

iot_nodes = config['iot_nodes']
iot_host = []
iot_port = []
for i in range(iot_nodes):
    iot_host.append(config['iot' + str(i+1)]['host'])
    iot_port.append(config['iot' + str(i+1)]['port'])

# Cola de mensajes de feedback para cada nodo IoT
message_queue = []
for i in range(iot_nodes):
    message_queue.append(queue.Queue())

# Buffer de entrada. Uno por aplicación.
q_app = []
buf_len = []
for i in range(num_app):
    q_app.append(queue.Queue()) # Buffer de entrada. Guarda todos los paquetes que recibe el nodo Fog
    buf_len.append(0) # Longitud del buffer

# Configuración de los procesadores del nodo IoT
# Crea un diccionario con la info de cada procesador
iot_num_proc = config['iot' + str(sys.argv[2])]['num_proc'] #Número de procesadores
battery = config['iot' + str(sys.argv[2])]['battery'] # Batería del nodo IoT
cola = config['iot' + str(sys.argv[2])]['cola'] # FIXME comprobar si esta bien
q_len = np.zeros(iot_num_proc)

iot_dic_processor={}
for i in range(1, iot_num_proc+1):
    iot_dic_processor['cap_' + str(i)] = config['iot' + str(sys.argv[2])]['processor' + str(i)]['capacity'] #Capacidad del procesador
    iot_dic_processor['q_' + str(i)] = queue.Queue() #Cola de paquetes del procesador en el Fog. Una por procesador en el Fog
    iot_dic_processor['q_proc_' + str(i)] = queue.Queue() #Indica el número de paquetes que componen un servicio (cache del procesador)
    iot_dic_processor['event_' + str(i)] = threading.Event() #Evento para despertar al procesador

# Configuration of the Fog node processors
# Create a dictionary with information about each processor
try:
    fog_num_proc = config['fog' + str(sys.argv[2])]['num_proc']  # Number of processors
    cola = config['fog' + str(sys.argv[2])]['cola']
    fog_dic_processor = {}
    for i in range(1, fog_num_proc + 1):
        fog_dic_processor['cap_' + str(i)] = config['fog' + str(sys.argv[2])]['processor' + str(i)]['capacity']  # Processor capacity
        fog_dic_processor['q_' + str(i)] = queue.Queue()  # Queue of packets for the processor in the Fog. One per processor in the Fog
        fog_dic_processor['q_proc_' + str(i)] = queue.Queue()  # Indicates the number of packets that make up a service (processor cache)
        fog_dic_processor['event_' + str(i)] = threading.Event()  # Event to wake up the processor
except:
    pass

event_service = []
for i in range(num_app):
    event_service.append(threading.Event()) # Event to wake up the packet generator when working with lognormal and slots. The service generator sends events.

# Counters
pkt_gen = 0
pkt_proc = 0
serv_proc = 0
pkt_sent = 0
problem = 0

HEADERLENSIZE = config['simulation']['HEADERLENSIZE']
IDSIZE = config['simulation']['IDSIZE']
PKTSERLEN = config['simulation']['PKTSERLEN']
LENSEV = config['simulation']['LENSEV']

traf_rate = config['simulation']['traf_rate']
pkt_len = config['simulation']['pkt_len']
traf_dist = config['simulation']['traf_dist']
serv_dist = config['simulation']['serv_dist']
pkt_len_dist = config['simulation']['pkt_len_dist']
sim_time = config['simulation']['sim_time'] *1.5
serv_rate = config['simulation']['serv_rate']
slot_time = config['simulation']['slot_time']
slot_number = np.floor(config['simulation']['sim_time']/slot_time)-1

serv_gen = 0

lock = threading.Lock()

serv_event = False
end_event = False
processing = np.full((4), False)

cloudInfo = [] # To store updated information about the Cloud nodes

import socket
def is_socket_closed(sock: socket.socket) -> bool:
    try:
        data = sock.recv(16, socket.MSG_DONTWAIT | socket.MSG_PEEK)
        if len(data) == 0:
            return True
    except BlockingIOError:
        return False
    except ConnectionResetError:
        return True
    except Exception as e:
        print("Unexpected exception when checking if a socket is closed")
        return False
    return False