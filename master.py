##  Autor: Neco Villegas Saiz
##  Universidad de Cantabria    
##  Fecha: 14/07/2022

'''
Implementa el nodo Master. Argumento fichero json

Se comunica con generador de servicios (service.py).
Recibe diccionarios con la situación actual de los nodos.
Devuelve asignación servicio-nodo. Formato local::<num procesador> o cloud::<num nodo>

Para implementar la lógica a la hora de asignar un nodo a cada servicio uso un Callable object en lugar de función en el master. Este objeto se encarga solo de la lógica del master, 
todo lo relacionado con recibir y enviar los diccionarios se encarga master.py. La clase tiene que llamarse igual que el fichero py e indicar el nombre en el json.
Ejemplos: RoundRobin, Aleatorio
'''

#######################################################################################################

import threading
import socket
import os
from random import randint, choices
from datetime import datetime, timedelta
import numpy as np
from time import sleep
import pickle
import math
import json
import sys
import logging
import log
import importlib

# TRAFIC CONTROL
##os.system('tc qdisc add dev eth0 root netem delay 10ms')

def write_output(info, file):
    f = open("./res/" + file, "a+")
    with f as jsonfile:
        json.dump(info, jsonfile, indent = 3)
        jsonfile.write('\n ****************************************************************** \n')

with open(str(sys.argv[1]), 'r') as jsonfile:
    config = json.load(jsonfile)

logger = log.setup_custom_logger('Master')
exec("logger.setLevel(logging.%s)" % (config['logger']['master']))

mod = importlib.import_module('alg.' + str(config['master']['algorithm']))
logger.info('Algorithm = ' + str(config['master']['algorithm']))

# Variables de configuración (json)
cl_nodes = config['cloud_nodes']
fog_nodes = config['fog_nodes']
sim_time = config['simulation']['sim_time']
slot_number = config['simulation']['slot_number'] - 1

#Crea socket
mysock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mysock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
mysock.bind(('0.0.0.0', config['master']['port']))
mysock.listen(5) #Numero de conexiones maximas en espera

from datetime import datetime, timedelta
def target_fun_one(conn, addr, tiempo, alg):
    global now
    global dic_request
    name = socket.gethostbyaddr(addr[0])[0] #Obtener el nombre de la ip origen
    logger.info('New connection: ' + str(name))
    name = name[name.find('_')+1:(name.find('.')-2)]
    conn.settimeout(2)
    #logger.info(str(name))
    t1 = datetime.now()

    num_slot = 0
    while True:
        t2 = datetime.now() 
        tt = (t2-t1).total_seconds()
        if num_slot == slot_number or tt > sim_time:
            #break
            return

        try:
            dic_request = pickle.loads(conn.recv(10000))
        except:
            continue

        if dic_request: #Los diccionarios vacios equivalen a falso
            write_output(dic_request, 'Request.txt') # Guardo en fichero la info que se recibe del nodo Fog

            num_slot = int(dic_request['service']['num_slot']) ###
            
            ## Aplica el algoritmo
            dic_response = alg(dic_request)
            write_output(dic_response, 'Response.txt')

            logger.info('Sending ' + str(dic_response) + ' to ' + str(name))
            conn.send(pickle.dumps(dic_response))
            dic_request.clear() # Vacia nuevamente la lista

tiempo = datetime.now()

conn = []
addr = []
h_recv = []

# Espera de nuevas conexiones
for i in range(fog_nodes): # Crea un thread para cada nodo Fog
    conn.append('')
    addr.append('')
    conn[i], addr[i] = mysock.accept()
    alg = eval('mod.' + config['master']['algorithm'] + '()')
    h_recv.append(threading.Thread(target=target_fun_one, args=(conn[i], addr[i], tiempo, alg)))
    logger.info('Starting target_fun_one')
    h_recv[i].start()

for i in range(fog_nodes):
    h_recv[i].join()
