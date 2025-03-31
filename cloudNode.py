'''
Implement Cloud node. Arguments are the json file and the Cloud ID.
'''

import socket
from datetime import datetime, timedelta
import threading, queue
from time import sleep
import os
import sys
import pickle
import json
import logging
import log
import shared_data
import time

logger = log.setup_custom_logger('Cloud')
exec("logger.setLevel(logging.%s)" % (shared_data.logCloud))

with open(str(sys.argv[1]), 'r') as jsonfile:
    config = json.load(jsonfile)
f = open("./res/Cloud" + str(sys.argv[2]) + ".txt", "a+") # Tracking services
f2 = open("./res/Utilizacion.txt", "a+")
f3 = open("./res/cloudQProc.txt", "a+")
HEADERLENSIZE = config['simulation']['HEADERLENSIZE']
IDSIZE = config['simulation']['IDSIZE']
PKTSERLEN = config['simulation']['PKTSERLEN']
LENSEV = config['simulation']['LENSEV']
proc_cap = config['cloud1']['capacity']
sim_time = config['simulation']['sim_time']
fog_nodes = config['fog_nodes']
iot_nodes = config['iot_nodes']
node_id = sys.argv[2]
# Create TCP socket
logger.debug('Creating socket')
mysock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mysock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
mysock.bind(('0.0.0.0', config['cloud' + str(sys.argv[2])]['port']))
mysock.listen()

# Create socket to send feedback messages
fog_control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
fog_control_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
logger.debug('socket.bind((0.0.0.0, ' + str(shared_data.cloud_control_port[0]) + '))')
fog_control_sock.bind(('0.0.0.0', shared_data.cloud_control_port[0]))
fog_control_sock.listen()
logger.debug('fog_control socket OK')

q = queue.Queue()
buffer = queue.Queue()
q_proc = queue.Queue()
q_serv = queue.Queue()
# Counter processed services
serv_proc = 0
processing = False
end = False

# Funcion receptora
def receiver(conn, addr):
    logger.debug('En receiver')
    global processing
    global end
    name = socket.gethostbyaddr(addr[0])[0] # Obtain name of the node
    name = name[name.find('_')+1:(name.find('.')-2)] 
    name_id = name[-1:]
    b_end_cont = 0
    while True:
        received_packets = []
        if end == True: # Close connection
            logger.debug('Closing connection')
            try:
                conn.close()
                logger.debug('Connection closed')
            except ValueError:
                logger.error('Error closing connection')
            #break
            return
        logger.debug('Waiting for data')
        data = conn.recv(222, socket.MSG_WAITALL)
        if data == b'':
            logger.debug('data vacio, break')
            end = True
            break
        data = data.decode("utf-8")
        received_packets.append(data)  # Decode and store data
        logger.debug('data = ' + str(data))
        b_end = data[HEADERLENSIZE+IDSIZE+1:HEADERLENSIZE+IDSIZE+1+1] # Byte end tx
        logger.debug('b_end = ' + str(b_end))
        if b_end == '1': # End tx
            logger.debug('Set end = True')
            b_end_cont += 1
            logger.debug(f'b_end = 1, at the moment I have {b_end_cont}')
            if b_end_cont == iot_nodes: # All IoT nodes have sent their b_end
                end = True
                break
        else:
            headerlen = data[:HEADERLENSIZE] # Header packet length
            logger.debug(f"headerlen = {headerlen} en data = {data}")
            if data[shared_data.HEADERLENSIZE:shared_data.HEADERLENSIZE + shared_data.IDSIZE] != '':
                pkts_serv = int(data[HEADERLENSIZE+IDSIZE+1+1:HEADERLENSIZE+IDSIZE+1+1+PKTSERLEN])
            else:
                logger.warning(f"Empty data, ignoring")
                break

            pkt = data[HEADERLENSIZE:HEADERLENSIZE+IDSIZE+PKTSERLEN+1+1+LENSEV]
            
            if pkts_serv > 1:
                data = conn.recv(222*(pkts_serv-1), socket.MSG_WAITALL)
                if len(data) != 222*(pkts_serv-1):
                    logger.error(f"Error, len(data) = {len(data)}, data = {data}")
                data = data.decode("utf-8")
                headerlen = data[:HEADERLENSIZE]
                received_packets.extend(data[i:i + 222] for i in range(0, len(data), 222))
                if len(received_packets[-1]) != 222:
                    logger.error(f"Error, len(received_packets[-1]) = {len(received_packets[-1])}, last packet = {received_packets[-1]}")

            q_proc.put(pkts_serv)
            for p in received_packets:
                headerlen = p[:HEADERLENSIZE]
                pkt = p[HEADERLENSIZE:HEADERLENSIZE+IDSIZE+PKTSERLEN+1+1+LENSEV]
                q.put(headerlen+pkt+name_id)

# Processor. Similar to processor.py
def processor(proc_cap, tiempo):
    global serv_proc, processing
    t_proc = 0
    total_len = 0
    t1 = datetime.now()
    logger.debug('Starting processor')
    while(True):
        if end == True:
            logger.debug('Cloud processor ended with success')
            f2.write('cloud::' + str(sys.argv[2]) + ',' + str(t_proc/ (datetime.now()-t1).total_seconds() *100) + '\n')
            f.close()
            f2.close()
            f3.close()
            shared_data.message_queue[0].put((99999, datetime.now().strftime("%H:%M:%S.%f"))) # No sé si hará falta. Cierra thread de envio mensajes control
            #break
            return
        if q_proc.qsize() != 0:
            logger.debug('Processing service')
            processing = True
            time_ini = datetime.now()
            serv_proc += 1
            num_pkts = q_proc.get()

            data = q.get()
            serv_id = data[HEADERLENSIZE+IDSIZE+1+1+PKTSERLEN:HEADERLENSIZE+IDSIZE+1+1+PKTSERLEN+LENSEV]
            if serv_id == '': # FIXME
                logger.error(f"ERROR serv_id empty, data = {data}")
                data = q.get()
                serv_id = int(data[HEADERLENSIZE+IDSIZE+1+1+PKTSERLEN:HEADERLENSIZE+IDSIZE+1+1+PKTSERLEN+LENSEV])
            else:
                serv_id = int(serv_id)
                
            pkt_len = data[:HEADERLENSIZE]
            if pkt_len == '':
                logger.error(f"ERROR pkt_len empty, data = {data}")
            else:
                pkt_len = int(pkt_len) # 10xxxxx0100211111111111
            # total_len += pkt_len
            if num_pkts > 1:
                for i in range(num_pkts-1):
                    data = q.get()
                    logger.debug(f'get, data={data}')
            
            total_len = pkt_len * num_pkts

            t_init = datetime.now().strftime("%H:%M:%S.%f")
            if total_len/proc_cap > 0.001:
                sleep(total_len/proc_cap)
            logger.debug(f"Service {serv_id} processed")

            # Send message to IoT node that the service with serv_id has finished processing
            time_f = datetime.now().strftime("%H:%M:%S.%f")
            shared_data.message_queue[0].put((serv_id, time_f)) # Index 0 because there is only one Cloud for now
            logger.debug(f"Mensaje enviado a IoT: {serv_id}")

            processing = False
            f.write(str(serv_id) + ',' + t_init + ',' + time_f + ',' + str(total_len) +'\n')
            time_end = datetime.now()
            foo = (time_end-time_ini).total_seconds()
            t_proc += foo
            total_len = 0

def notify_fog_node(conn, addr, id):
    while True:
        # Wait until there is a message in the queue
        logger.debug("Esperando para get()")
        message = shared_data.message_queue[id].get()
        serv_id, time = message
        logger.debug(f"Mensaje: {message}")
        if serv_id == 99999:
            conn.close()
            return
        try:
            delimiter = b'\xff'
            header = bytes([0x01 + (serv_id // 1000 - 1)])
            message = delimiter + header + f"{serv_id},{time}".encode('utf-8')
            logger.debug(f"Message to IoT: {message}")
            conn.send(message)
        except Exception as e:
            logger.error(f"Error: {e}")

class sender():
    def __init__(self):
        self.proc_cap=proc_cap
        self.node_id=node_id
        self.fog=False

def write_qProc(file):
    while end == False:
        file.write('cloud' + '1' + ',' + datetime.now().strftime("%H:%M:%S.%f") + ',')
        file.write(str(q.qsize()) + '\n')
        sleep(.5)

# Main         
logger.info('Starting Cloud')  
tiempo = datetime.now()
h_proc = threading.Thread(name="hilo_proc", target=processor, args=(proc_cap, tiempo)) #Hilo para procesar datos de la cola
h_write_qProc = threading.Thread(name="write_qProc", target=write_qProc, args=(f3,))
h_proc.start()
h_write_qProc.start()
conn = []
addr = []
conn_control = []
addr_control = []
h1 = []
h2 = []
# Wait for connections
logger.debug('Esperando conexiones')
for i in range(fog_nodes):
    conn.append('')
    addr.append('')
    conn_control.append('')
    addr_control.append('')
    conn[i], addr[i] = mysock.accept()
    h1.append(threading.Thread(target=receiver, args=(conn[i], addr[i])))
    h1[i].start()
    conn_control[i], addr_control[i] = fog_control_sock.accept()
    shared_data.message_queue.append(queue.Queue())
    h2.append(threading.Thread(target=notify_fog_node, args=(conn_control[i], addr_control[i], i,)))
    h2[i].start()
for i in range(fog_nodes):
    logger.debug('join receiver')
    h1[i].join()
    logger.debug('join notify_fog_node')
    h2[i].join()

logger.debug('join proc')
h_proc.join()
logger.debug('h_proc finished')

fog_control_sock.close()

logger.info('Cloud ended with success')