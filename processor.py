##  Author: Neco Villegas
##  Universidad de Cantabria    
##  Date: 12/07/2022

''' Multiprocessor system.

Each processor is modeled as a thread with its own queue and a "processor cache" (q_proc), 
which holds the packets to be processed.
'''

from time import sleep
from datetime import datetime
import shared_data
import logging
import log
import time
import queue

# Set up a custom logger for the processor
logger = log.setup_custom_logger('Processor')
exec("logger.setLevel(logging.%s)" % (shared_data.logProcessor))

# Main processor function: processes (remove + sleep) traffic from its assigned queue
def processor(proc_cap, q, q_proc, event, num, node_name):
    logger.debug( str(num+1) +'-- Processor ' + str(num+1) + ' in ' + node_name + ' ' + str(shared_data.sys.argv[2]) +  ' started')

    # File to log service tracking
    f = open('./res/' + node_name + str(shared_data.sys.argv[2])  + 'proc' + str(num+1) + '.txt', 'a+')

    t_init_sim = datetime.now()
    t_proc = 0      # Time spent processing
    pkt_proc = 0    # Number of packets processed
    serv_proc = 0   # Number of services processed
    total_len = 0   # Total packet length processed

    # Processing loop: runs until global finish event is set
    while shared_data.end_event == False:
        logger.debug('proc' + str(num+1) + ' | q_proc.qsize() = ' + str(q_proc.qsize()))
         # See the ‘service’ (or `receiver`) function: q_proc.put(buff_size) signals that a service with buff_size packets is ready
        if q_proc.qsize() != 0:
            time_ini = datetime.now()
            shared_data.processing[num] = True  # Mark processor as busy
            serv_proc += 1
            # Get the number of packets to process for this service
            num_pkts = q_proc.get()
            logger.debug(f"proc{num+1} | Process service of {num_pkts} pkts")
            # Process all packets belonging to this service
            for i in range(num_pkts):
                try:
                    data = None
                    data = q.get(block=False) # Get pkt from queue
                    logger.debug('proc' + str(num+1) + ' proccessing pkt ' + str(i+1) + ' of ' + str(num_pkts))                    
                    id_serv_actual = data[shared_data.HEADERLENSIZE+shared_data.IDSIZE+1+1+shared_data.PKTSERLEN:shared_data.HEADERLENSIZE+shared_data.IDSIZE+1+1+shared_data.PKTSERLEN+shared_data.LENSEV]
                    id_pkt_actual = data[shared_data.HEADERLENSIZE:shared_data.HEADERLENSIZE+shared_data.IDSIZE]
                    if i > 0 and int(id_pkt_actual) > 1 and id_serv_actual != '99999' and id_serv_anterior != '99999':
                        logger.debug(f"Error en el procesador si {id_serv_actual} != {id_serv_anterior}")
                        if id_serv_actual != id_serv_anterior:
                            logger.error(f"ERROR in proc{num+1}: {id_serv_actual} != {id_serv_anterior} (pkt {id_pkt_actual} of service {id_serv_actual})")
                            break
                    id_serv_anterior = id_serv_actual

                except queue.Empty:
                    # Manejar la excepción cuando la cola está vacía
                    logger.debug(f"The queue is empty and it must have {num_pkts} pkts, waiting them...")
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"ERROR in proc{num+1}: {e}")
                    break
                with shared_data.lock:
                    logger.debug(f'proc{num+1} gets lock')
                if data is None:
                    logger.debug("Error: data is None")
                    serv_id = None
                    continue
                if i == 0 and shared_data.end_event == False:
                    serv_id = int(data[shared_data.HEADERLENSIZE+shared_data.IDSIZE+1+1+shared_data.PKTSERLEN:shared_data.HEADERLENSIZE+shared_data.IDSIZE+1+1+shared_data.PKTSERLEN+shared_data.LENSEV]) #solo cojo el serv_id una vez
                pkt_len = int(data[:shared_data.HEADERLENSIZE])
                total_len += pkt_len
                sleep(pkt_len/proc_cap) # Sleeps according to the defined processing capacity
                pkt_proc += 1
                shared_data.pkt_proc += 1
                logger.debug( str(num+1) +'-- Packet processed (' + str(pkt_proc) + ')')
            t_init = datetime.now().strftime("%H:%M:%S.%f")
            logger.debug('proc' + str(num+1) + ' | sleep(' + str(total_len/proc_cap) + ')')
            try:
                f.write(str(serv_id) + ',' + t_init + ',' + datetime.now().strftime("%H:%M:%S.%f") + ',' + str(total_len) + '\n')
            except:
                pass
            
            # Send message to IoT node indicating that service serv_id has finished processing
            if serv_id is None:
                continue
            if node_name == 'fog':
                # Define a dictionary to map serv_id ranges to corresponding header values and queues
                serv_id_to_queue = {
                    range(1000, 1999): (b'\x01', 0), range(2000, 2999): (b'\x02', 1),
                    range(3000, 3999): (b'\x03', 2), range(4000, 4999): (b'\x04', 3),
                    range(5000, 5999): (b'\x05', 4), range(6000, 6999): (b'\x06', 5),
                    range(7000, 7999): (b'\x07', 6), range(8000, 8999): (b'\x08', 7),
                    range(9000, 9999): (b'\x09', 8), range(10000, 10999): (b'\x0A', 9),
                    range(11000, 11999): (b'\x0B', 10), range(12000, 12999): (b'\x0C', 11),
                    range(13000, 13999): (b'\x0D', 12), range(14000, 14999): (b'\x0E', 13),
                    range(15000, 15999): (b'\x0F', 14), range(16000, 16999): (b'\x10', 15),
                    range(17000, 17999): (b'\x11', 16), range(18000, 18999): (b'\x12', 17),
                    range(19000, 19999): (b'\x13', 18), range(20000, 20999): (b'\x14', 19)
                }
                for serv_range, (header, queue_index) in serv_id_to_queue.items():
                    if serv_id in serv_range:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")
                        message = header + f"{serv_id},{timestamp}".encode('utf-8')
                        logger.debug(f"Service processed, sending message to IoT node: {message}")
                        shared_data.message_queue[queue_index].put(message)
                        break
            else:
                time_i = datetime.strptime(shared_data.services_gen[int(serv_id)], "%H:%M:%S.%f")
                time_f = datetime.strptime(datetime.now().strftime("%H:%M:%S.%f"), "%H:%M:%S.%f")
                time_difference = (time_f - time_i).total_seconds() * 1000
                logger.debug(f"{serv_id} tardo {time_difference} ms")
                shared_data.serv_time_results[int(serv_id)] = time_difference

            logger.debug( str(num+1) +'-- Local queue = ' + str(shared_data.q_len[num]))
            shared_data.processing[num] = False # Processor is now free
            time_fin = datetime.now()
            foo = (time_fin-time_ini).total_seconds()
            t_proc += foo
            total_len = 0
        else: # No services to process
            if shared_data.end_event == True:
                return
            event.clear()
        if shared_data.end_event == True:
            return
        event.wait(timeout=None)
    
    logger.debug( str(num+1) +'-- Processor ended with success, services processed = ' + str(serv_proc))
    f.close()