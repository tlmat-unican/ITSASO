"""
Implements a Fog node. Takes a JSON file and Fog ID as arguments.

Creates multiple threads:
- One thread per processor (processor.py)
- Rx packets from IoT nodes (receiver.py)
- Several threads to send information to IoT nodes

Uses the shared_data module to read configuration from the JSON file and handle shared variables. All threads have access to it.

Keeps track of the simulation time and notifies threads and Cloud nodes when the simulation ends.
"""

from time import sleep
import threading, queue
from datetime import datetime, timedelta
import socket
import os
import pickle
import shared_data
import logging
import log
import processor
import time
import re
import struct

def wait_for_socket(fog_sock, i, host, port, timeout=60):
    start_time = time.time()
    fog_sock.append(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    try:
        fog_sock[i].setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        fog_sock[i].setsockopt(socket.SOL_SOCKET, 36, struct.pack('I', 1)) # Mark the socket with 1 to introduce the delay towards the Cloud
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

delay = shared_data.delay_fog_cloud[0] # ms. Delay Fog-Cloud
os.system('tc qdisc add dev eth0 root handle 1: prio')
os.system(f'tc qdisc add dev eth0 parent 1:1 handle 10: netem delay {str(delay)}ms')
os.system('tc filter add dev eth0 parent 1:0 protocol ip prio 1 handle 1 fw flowid 1:1')
logger = log.setup_custom_logger('Fog')
exec("logger.setLevel(logging.%s)" % (shared_data.logNodoFog))
logger.info('Nodo Fog starts')
f = open("./res/" + 'fogQProc.txt', "a+")
logger.debug('Creating socket')

# Create TCP socket
iot_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
iot_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
logger.debug('socket.bind((0.0.0.0, ' + str(shared_data.fog_port[0]) + '))')
iot_sock.bind(('0.0.0.0', shared_data.fog_port[0])) # TODO
iot_sock.listen(20)
logger.debug('IoT socket OK')

# Create a TCP socket to send control messages to the IoT nodes
iot_control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
iot_control_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
logger.debug('socket.bind((0.0.0.0, ' + str(shared_data.fog_control_port[0]) + '))')
iot_control_sock.bind(('0.0.0.0', shared_data.fog_control_port[0]))
iot_control_sock.listen()
logger.debug('IoT_control socket OK')

# Create TCP socket to send data to Cloud
cloud_sock = []
for i in range(shared_data.cloud_nodes):
    logger.debug('Connecting to Cloud ' + str(i+1) + ' -> socket.connect(' + str(shared_data.cloud_host[i]) + ', ' + str(shared_data.cloud_port[i]) + ')')
    wait_for_socket(cloud_sock, i, shared_data.cloud_host[i], shared_data.cloud_port[i], timeout=360)


# Create TCP socket to send control messages to Cloud
cloud_control_sock = []
for i in range(shared_data.cloud_nodes):
    cloud_control_sock.append(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    logger.debug('Connecting to Cloud ' + str(i+1) + ' -> socket.connect(' + str(shared_data.cloud_host[i]) + ', ' + str(shared_data.cloud_control_port[0]) + ')')
    cloud_control_sock[i].connect((shared_data.cloud_host[i], shared_data.cloud_control_port[0]))

# Create processor threads
hp = []
for i in range(1, shared_data.fog_num_proc+1):
    logger.info('Starting processor ' +  str(i) + '...')
    hp.append(threading.Thread(name=["hilo_0." + str(i)], target=processor.processor, args=(shared_data.fog_dic_processor['cap_' + str(i)], shared_data.fog_dic_processor['q_' + str(i)], shared_data.fog_dic_processor['q_proc_' + str(i)], shared_data.fog_dic_processor['event_' + str(i)], (i-1), 'fog'))) #Hilo para procesar paquetes de la cola. args = (capacidad, cola, cache)
    hp[i-1].start()

# Write processor queue length to file
def write_qProc(f):
    f.write('fog' + '1' + ',' + datetime.now().strftime("%H:%M:%S.%f") + ',')
    for i in range(1,shared_data.fog_num_proc+1):
        if i != shared_data.fog_num_proc:
            f.write(str(shared_data.fog_dic_processor['q_' + str(i)].qsize()) + ',')
        else:
            f.write(str(shared_data.fog_dic_processor['q_' + str(i)].qsize()) + '\n')

def collect_info():
        # Gather information about the node to send to IoT
        fogInfo = {}
        fogInfo['num_proc'] = shared_data.fog_num_proc
        fogInfo['id'] = int(shared_data.sys.argv[2])
        for i in range(1, shared_data.fog_num_proc+1): # Create one dictionary per processor
            fogInfo['proc' + str(i)] = {'q_len': shared_data.fog_dic_processor['q_' + str(i)].qsize(), 'proc_cap': shared_data.fog_dic_processor['cap_' + str(i)]}
        logger.debug(f"fogInfo = {fogInfo}")
        return fogInfo

q = queue.Queue()
q_proc = queue.Queue()

# Receive packets from IoT nodes
def receiver(conn, addr):
    b_end_cont = 0
    end = False
    name = socket.gethostbyaddr(addr[0])[0] # Obtain the name of the IoT node
    name = name[name.find('_')+1:(name.find('.')-2)]
    while not end:
        write_qProc(f)
        received_packets = [] # List to store received packets
        pkt_aux = conn.recv(222, socket.MSG_WAITALL)
        logger.debug(f'Paquete recibido {pkt_aux}')
        rem_data = b''
        if pkt_aux == b'':
            logger.debug('No data received')
            break
        received_packets.append(pkt_aux.decode('utf-8'))  # Decode the packet and store it in the list

        pkts_serv = int(received_packets[0][shared_data.HEADERLENSIZE:][shared_data.IDSIZE+1+1:shared_data.IDSIZE+1+1+shared_data.PKTSERLEN])

        if pkts_serv > 1:
            pkt_aux = conn.recv(222*(pkts_serv-1), socket.MSG_WAITALL)
            logger.debug(f"Recibido el resto de paquetes (recv de {222*(pkts_serv-1)}): {pkt_aux}")
            received_packets.extend(pkt_aux.decode('utf-8')[i:i + 222] for i in range(0, len(pkt_aux), 222))

        logger.debug(f'pkts_serv = {pkts_serv}, len(received_packets) = {len(received_packets)}')

        data_to_send_list = []
        for i in range(pkts_serv):
            try: # FIXME comprobar si alguna vez da este error
                data = received_packets[i]
            except:
                logger.error(f"i = {i} is not in received_packets = {received_packets}, pkts_serv = {pkts_serv}")
                break
            headerlen = data[:shared_data.HEADERLENSIZE] # Header with the length of the packet
            if len(data[:shared_data.HEADERLENSIZE]) < shared_data.HEADERLENSIZE: # Volver a leer si no hay paquetes completos para procesar
                rem_data = data
                break
            data = data[shared_data.HEADERLENSIZE:]  # id + flag + end + pkts/serv + serv_id + data
            try:
                headerlen_int = int(headerlen)
            except ValueError:
                logger.error(f"Invalid header length: {headerlen}")
                continue
            if len(data) >= (headerlen_int + shared_data.IDSIZE + shared_data.PKTSERLEN + 1 + 1 + shared_data.LENSEV):
                pkt = data[:(int(headerlen)+shared_data.IDSIZE+shared_data.PKTSERLEN+1+1+shared_data.LENSEV)] #Datos por paquete
                flag = data[shared_data.IDSIZE:shared_data.IDSIZE+1]
                logger.warning(str(headerlen+pkt))
                logger.debug('flag = ' + flag + ' (1 es cloud) en ' + str(data))
                if (flag != '1'): # Process in the Fog
                    if int(data[:shared_data.IDSIZE]) == (i+1):
                        shared_data.fog_dic_processor['q_' + '1'].put(headerlen+pkt)
                        logger.debug(f'pkt {data[:shared_data.IDSIZE]} de {data[shared_data.IDSIZE+1+1+shared_data.PKTSERLEN:shared_data.IDSIZE+1+1+shared_data.PKTSERLEN+shared_data.LENSEV]} a procesador')
                    b_end = data[shared_data.IDSIZE+1:shared_data.IDSIZE+1+1]

                    logger.debug(f"El servicio {data[shared_data.IDSIZE+1+1+shared_data.PKTSERLEN:shared_data.IDSIZE+1+1+shared_data.PKTSERLEN+shared_data.LENSEV]} tiene {pkts_serv} paquetes")
                    logger.debug(f'q = {shared_data.fog_dic_processor["q_" + "1"].qsize()}, pkts_serv = {pkts_serv}')
                    if i+1 == pkts_serv: # If the entire service is in the processor queue (the last packet has been queued in this iteration), it wakes it up.
                        shared_data.fog_dic_processor['q_proc_' + '1'].put(pkts_serv) # Inform the processor of the number of packets in the service to process. For now, only the first processor is considered.
                        shared_data.fog_dic_processor['event_' + '1'].set() # Wake up the corresponding processor
                        logger.debug('Wake up processor 1')

                    if b_end != '0':
                        logger.debug(f'Rx b_end = {b_end}')
                        end = True
                        conn.close()
                        break
                    else:
                        pass
                    logger.debug(f"Finished reading the headers of pkt {data[:shared_data.IDSIZE]} and sending it to the processor")

                else: # Process in Cloud
                    t_ini = datetime.now()
                    serv_id = int(pkt[shared_data.IDSIZE+1+1+shared_data.PKTSERLEN:shared_data.IDSIZE+1+1+shared_data.PKTSERLEN+shared_data.LENSEV])
                    data_to_send = (headerlen+pkt).encode()
                    logger.debug(f'data to send = {data_to_send}')
                    if serv_id == 99999: # Ending the simulation
                        logger.debug(f'Sending END packet to Cloud: {data_to_send}')
                        cloud_sock[0].sendall(data_to_send)
                        b_end_cont += 1
                        logger.debug(f'b_end += 1, at the moment I have {b_end_cont} / {shared_data.iot_nodes}')
                        if b_end_cont >= shared_data.iot_nodes:
                            logger.debug('All IoT nodes have sent their b_end')
                            end = True
                            shared_data.end_event = True
                            break

                    data_to_send_list.append(data_to_send)

                    if i == pkts_serv-1:
                        data_to_send_combined = b''.join(data_to_send_list)
                        logger.debug(f'Enviados todos los paquetes al Cloud {data_to_send_combined}')
                        cloud_sock[0].sendall(data_to_send_combined)
                        sleep(delay/1000)
            else:
                # rem_data = headerlen + data
                break
    # Close connection
    logger.debug('Closing connection')
    try:
        conn.close()
        logger.debug('Connection closed')
    except ValueError:
        logger.error('Error closing connection')

def send_info(conn, addr):
    while conn.fileno() != -1 and shared_data.end_event == False:
        fogInfo = collect_info()

        serialized_fogInfo = pickle.dumps(fogInfo)
        if b'\xff' in serialized_fogInfo:
            logger.debug(f'fogInfo = {serialized_fogInfo}')
            continue
        try:
            req = conn.recv(6).decode("utf-8")
            logger.debug('req = ' + str(req))
            if req == 'ExitRq':
                logger.debug('ExitRq received')
                break
            elif req == 'InfoRq':
                conn.send(b'\xff' + pickle.dumps(fogInfo))
                logger.debug('FogInfo sent to IoT')
            elif req == '':
                pass
            else: # Rx id from IoT node
                shared_data.conns[int(req)-1] = conn
        except pickle.UnpicklingError:
            logger.error('Error unpickling data')
        except ConnectionResetError:
            logger.warning('Connection was reset by peer')
            break
        # sleep(shared_data.slot_time)
        sleep(shared_data.slot_time/2) # 2 reports per slot

def notify_iot_node(conn, addr, i):
    while conn.fileno() != -1 or shared_data.end_event == False:
        # Waiting for message in the queue
        logger.debug(f"Esperando para get() en cola {i}")
        data = shared_data.message_queue[i].get()
        header = data[:1]  # The first byte is the header
        try:
            decoded_data = data[1:].decode('utf-8', errors='replace')
        except:
            logger.error(f"ERROR while decoding {data[1:]}")
            continue
        serv_id, time = decoded_data.split(',')
        if int(serv_id) == 99999:
            conn.close()
            return
        try:
            header = b'\xff' + header
            message = header + f"{serv_id},{time}".encode('utf-8')
            conn.send(message)
        except Exception as e:
            logger.error(f"Error: {e}")

# Rx feedback from the Cloud
def handle_cloud_messages(socket_lock):
    header_to_queue_index = { # NOTE max 20 IoT nodes
        b'\x01': 0, b'\x02': 1, b'\x03': 2, b'\x04': 3, b'\x05': 4,
        b'\x06': 5, b'\x07': 6, b'\x08': 7, b'\x09': 8, b'\x0A': 9,
        b'\x0B': 10, b'\x0C': 11, b'\x0D': 12, b'\x0E': 13, b'\x0F': 14,
        b'\x10': 15, b'\x11': 16, b'\x12': 17, b'\x13': 18, b'\x14': 19,
        # Add more if needed
    }
    while shared_data.end_event == False:
        try:
            logger.debug("Waiting feedback from Cloud")
            data = cloud_control_sock[0].recv(1024) # NOTE index 0 because there is only one Cloud node for now
            if not data:
                logger.info("Conexión cerrada por el nodo Fog")
                break
        except ConnectionResetError:
            logger.error("Conexión reiniciada por el nodo Cloud.")
            break
        except OSError as e:
            logger.error(f"Error del socket: {e}")
            break
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            break
        delimiter = b'\xff'
        blocks = re.split(delimiter, data)
        blocks = [block for block in blocks if block] # Remove empty blocks
        for d in blocks:
            header = d[:1]  # The first byte is the header
            # Resend the message to the corresponding IoT node
            if header in header_to_queue_index:
                try:
                    decoded_data = d[1:].decode('utf-8', errors='replace')
                    serv, time = decoded_data.split(',')
                    queue_index = header_to_queue_index[header]
                    logger.debug(f"Received from Cloud that service {serv} has been processed at {time}, sending {d} to queue {queue_index}")
                    shared_data.message_queue[queue_index].put(d)
                except:
                    logger.error(f"ERRO while decoding: {d[1:]}")
    try:
        cloud_control_sock[0].close()
        logger.info("Socket closed successfully")
    except Exception as e:
        logger.error(f"ERROR while closing socket: {e}")

## Create one thread per IoT node
conn_h2 = []
addr_h2 = []
h2 = []
h3 = []
for i in range(shared_data.iot_nodes):
    # conn.append('')
    # addr.append('')
    conn_i, addr_i = iot_control_sock.accept()
    conn_h2.append(conn_i)  # Save the connection socket
    addr_h2.append(addr_i)  # Save the client address
    logger.debug('Socket accept')
    h2.append(threading.Thread(target=send_info, args=(conn_i, addr_i))) # Send information to IoT nodes
    h2[i].start()
while len(shared_data.conns.keys()) != shared_data.iot_nodes:
    sleep(1e-3)
for i in range(shared_data.iot_nodes):
    shared_data.message_queue.append(queue.Queue())
    logger.debug(f'Creating thread to send control info to IoT node {i}')
    h3.append(threading.Thread(target=notify_iot_node, args=(shared_data.conns[i], '', i,))) # Notificar al nodo IoT correspondiente
    h3[i].start()

conn = []
addr = []
h1 = []
for i in range(shared_data.iot_nodes):
    conn.append('')
    addr.append('')
    conn_i, addr_i = iot_sock.accept()
    conn.append(conn_i)
    addr.append(addr_i)
    logger.debug('Socket accept')
    h1.append(threading.Thread(target=receiver, args=(conn_i, addr_i))) # Rx packets from IoT nodes
    h1[i].start()

# Rx feedback from the Cloud
socket_lock = threading.Lock()
h4 = threading.Thread(target=handle_cloud_messages, args=(socket_lock,)) # Recibir mensajes de Cloud y redirigir al nodo IoT correspondiente
h4.start()

for i in range(shared_data.iot_nodes):
    logger.debug('join receiver')
    h1[i].join()
logger.debug('Receiver thread finished')

## END OF SIMULATION
# Need to notify threads and Cloud nodes that the simulation has ended
# end_event variable accessible by all threads
# end_event=True ends some threads
# In the case of processors, they need to be awakened. They are scheduled to finish processing the queue even if the simulation time has ended
# Cloud nodes need to be sent a final byte (b_end) to inform them of the end of the simulation
tiempo = datetime.now()
tf = tiempo + timedelta(seconds=shared_data.sim_time)
logger.info('Simulation ended with success')
shared_data.end_event = True # Para indicar al resto de funciones que terminen
for i in range(1, shared_data.fog_num_proc+1): # Despierta a todos los procesadores para terminar todos los threads
    shared_data.fog_dic_processor['event_' + str(i)].set()

for i in range(shared_data.iot_nodes):
    shared_data.message_queue[i].put(b'\xff' + f'{99999},{datetime.now().strftime("%H:%M:%S.%f")}'.encode('utf-8')) # No sé si hará falta. Cierra el thread encargado de los mensajes de control

# Cierra todas las conexiones
logger.debug('Closing sockets')
iot_sock.close()
iot_control_sock.close()
cloud_sock[0].close()
logger.debug('Sockets closed')

logger.debug('join send_info threads')
for i in range(shared_data.iot_nodes):
    h2[i].join()
logger.debug('send_info threads finished')

logger.debug('join notify_iot_node threads')
for i in range(shared_data.iot_nodes):
    h3[i].join()
logger.debug('notify_iot_node threads finished')

logger.debug('Waiting for handle_cloud_messages threads')
h4.join()
logger.debug('handle_cloud_messages threads finished')

logger.debug('Waiting for processor thread')
for i in range(shared_data.fog_num_proc):
    shared_data.fog_dic_processor['event_' + str(i+1)].set()
    hp[i].join()
logger.debug('Processor thread finished')

# Log some information at the end of the simulation
logger.info(str(shared_data.pkt_proc) + ' packets processed')
for i in range(1, shared_data.fog_num_proc+1):
    logger.debug(str(shared_data.fog_dic_processor['q_' + str(i)].qsize()) + ' packets in processor' + str(i) + ' queue (FOG)')
for i in range(shared_data.num_app):
    logger.debug('App' + str(i+1) + ' ha generado ' + str(shared_data.cont_paq[i]) + ' paquetes')
f.close()
active_threads = threading.enumerate()
logger.debug(f"Active threads: {[thread.name for thread in active_threads]}")
logger.info('Fog ended with success')