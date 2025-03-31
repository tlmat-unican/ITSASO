'''
Implement IoT node. Arguments: json file and IoT id

Create multiple threads:
Traffic generator (trafficGen.py)
Service generator (service.py)

Shared_data module to read configuration from the json file and handle shared variables. All threads can access it.

Keeps track of simulation time and notifies threads and Cloud nodes of the end of the simulation.
'''

from time import sleep
import threading, queue
from datetime import datetime, timedelta
import socket
import os
import numpy as np
import pickle
import sys
import shared_data
import logging
import log
import processor
import service
import importlib
import time

def wait_for_socket(fog_sock, i, host, port, timeout=60):
    start_time = time.time()
    fog_sock.append(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    try:
        fog_sock[i].setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Desactivar el algoritmo Nagle
        while time.time() - start_time <= timeout:
            try:
                fog_sock[i].connect((host, port))
                logger.debug(f"Socket {host}:{port} is open")
                return True
            except ConnectionRefusedError:
                logger.warning(f"Connection refused while waiting for socket {host}:{port} to open")
            except Exception as e:
                logger.warning(f"An error occurred while waiting for socket {host}:{port} to open: {e}")
            time.sleep(1)
        logger.error(f"Timeout reached while waiting for socket {host}:{port} to open")
        return False
    except Exception as e:
        logger.error(f"An error occurred while setting up socket: {e}")
        return False

logger = log.setup_custom_logger('Iot')
exec("logger.setLevel(logging.%s)" % (shared_data.logIot))

traffic_mod = importlib.import_module(shared_data.traf_gen) # Importa módulo generador de tráfico

logger.debug('Nodo IoT starts')

sleep(.5)
fog_sock = [] # Create an empty list to store as many entries as there are connections
for i in range(shared_data.fog_nodes): # Create a connection with each involved Fog node
    wait_for_socket(fog_sock, i, shared_data.fog_host[i], shared_data.fog_port[i])

logger.debug(str(shared_data.fog_nodes) + ' socket(s) opened with Fog layer')

for i in range(shared_data.fog_nodes):
    fog_control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logger.debug('Connecting to Fog ' + str(i+1) + ' -> socket.connect(' + str(shared_data.fog_host[i]) + ', ' + str(shared_data.fog_control_port[0]) + ')')
    fog_control_sock.connect((shared_data.fog_host[i], shared_data.fog_control_port[0]))

cloud_sock = [] # Create an empty list to store as many entries as there are connections
for i in range(shared_data.cloud_nodes): # Create a connection with each involved Fog node
    cloud_sock.append(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    cloud_sock[i].setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    logger.debug('Connecting to Cloud ' + str(i))
    cloud_sock[i].connect((shared_data.cloud_host[i],shared_data.cloud_port[i]))
logger.debug(str(shared_data.cloud_nodes) + ' socket(s) opened with Cloud layer')

# Create the threads: processor, trafficGen (one per application), and service

## Processor
hp = []
for i in range(1, shared_data.iot_num_proc+1):
    logger.info('Starting processor ' +  str(i) + '...')
    hp.append(threading.Thread(name=["hilo_0." + str(i)], target=processor.processor, args=(shared_data.iot_dic_processor['cap_' + str(i)], shared_data.iot_dic_processor['q_' + str(i)], shared_data.iot_dic_processor['q_proc_' + str(i)], shared_data.iot_dic_processor['event_' + str(i)], (i-1), 'iot'))) #Hilo para procesar paquetes de la cola. args = (capacidad, cola, cache)
    hp[i-1].start()

## Service generator
service.fog_sock = fog_sock # TODO revisar
service.fog_control_sock = fog_control_sock # TODO revisar
service.cloud_sock = cloud_sock # TODO revisar
logger.debug('Starting service generator...')
hs = threading.Thread(name="hilo_2", target=service.service, args=(int(sys.argv[2]),)) # Thread to generate events for a new service
hs.start()

## Traffic generator
ht = []
for i in range(shared_data.num_app):
    logger.debug('Starting traffic generator ' +  str(i+1) + '...')
    ht.append(threading.Thread(name="hilo_1", target=traffic_mod.trafficGen, args=(i,shared_data.event_service[i]))) #Hilo para generar trafico
    ht[i].start()

## END OF SIMULATION
# Need to notify threads and Cloud nodes that the simulation has ended
# end_event variable accessible by all threads
# end_event=True causes both generators (traffic and services) to terminate
# For processors, they need to be awakened. They are programmed to finish processing the queue even if the simulation time has ended
# To Cloud nodes, a final byte (b_end) needs to be sent to inform them of the end of the simulation
ti = datetime.now()
tf = ti + timedelta(seconds=shared_data.sim_time)
while True:
    if shared_data.serv_gen > shared_data.slot_number or datetime.now() > tf:
        logger.debug('Simulation ended with success (' + str(shared_data.serv_gen) + ' slots), join threads')
        shared_data.end_event = True # Para indicar al resto de funciones que el tiempo de simulacion ha terminado
        for i in range(1, shared_data.iot_num_proc+1): # Despierta a todos los procesadores para terminar todos los threads
            shared_data.iot_dic_processor['event_' + str(i)].set()
        b_end = 1 # Activar flag b_end.
        shared_data.pkt_gen += 1
        logger.debug('Sending last byte to cloud')
        data = '0' * 200
        pkt_id = format(shared_data.pkt_gen, '0' + str(shared_data.IDSIZE) + 'd')
        header = format(200, '0' + str(shared_data.HEADERLENSIZE) + 'd') + pkt_id + '1' + str(b_end) + '00002' + '99999' # Pongo pkts_serv = 2 para que el fog reciba su b_end
        data = header + data #Header + data
        delay_index = shared_data.serv_gen % len(shared_data.delay[int(sys.argv[2])-1])
        delay = int(shared_data.delay[int(sys.argv[2])-1][delay_index])
        for i in range(shared_data.cloud_nodes):
            logger.info('Send b_end to Cloud node')
            try:
                logger.debug('Last pkt send to cloud ' + str(data.encode()))
                fog_sock[i].send(data.encode()) # Avisa a Cloud de que termine
            except:
                logger.error('Not possible to send b_end to Cloud node')
        header = format(200, '0' + str(shared_data.HEADERLENSIZE) + 'd') + pkt_id + '0' + str(b_end) + '00001' + '99999'
        data = '0' * 200
        data = header + data #Header + data
        for i in range(shared_data.fog_nodes):
            logger.info('Send b_end to Fog node')
            try:
                logger.debug('Last pkt send to fog ' + str(data.encode()))
                fog_sock[i].send(data.encode()) # Avisa a Fog de que termine
            except Exception as e:
                logger.error('Not possible to send b_end to Fog node: ' + str(e))
            try:
                fog_control_sock.send("ExitRq".encode())
                logger.debug("Sending InfoExit")
            except Exception as e:
                logger.error(f"ERROR sending InfoExit: {e}")
        sleep(10) # Allow some more time for the last packets to be sent while closing all threads of all nodes

        # Close all sockets
        logger.debug('Closing sockets')
        for i in range(len(cloud_sock)):
            cloud_sock[i].close()
        for i in range(len(fog_sock)):
            fog_sock[i].close()
        fog_control_sock.close()
        logger.debug('Sockets closed')
        break
    sleep(1)

# Wait for all threads to finish
# active_threads = threading.enumerate()
# logger.debug(f"Active threads: {[thread.name for thread in active_threads]}")
for i in range(shared_data.num_app):
    hp[i].join()
logger.debug('Processor thread finished')
for i in range(shared_data.num_app):
    ht[i].join()
logger.debug('Traffic thread finished')
hs.join()
logger.debug('Service thread finished')

# Show some logs at the end of the simulation
logger.debug(str(shared_data.pkt_proc) + ' packets processed')
for i in range(1, shared_data.iot_num_proc+1):
    logger.debug(str(shared_data.iot_dic_processor['q_' + str(i)].qsize()) + ' packets in processor' + str(i) + ' queue')
for i in range(shared_data.num_app):
    logger.debug('App' + str(i+1) + ' ha generado ' + str(shared_data.cont_paq[i]) + ' paquetes')
logger.debug(f"{shared_data.cont_serv_success}/{shared_data.serv_gen} processed services in less than 1 second")
logger.debug('IoT devices ended with sucess')