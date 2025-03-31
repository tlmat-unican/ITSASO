''' Traffic generator (packets).
- POISSON
- CONT
'''

from time import sleep
import threading, queue
from datetime import datetime, timedelta
import socket
import os
import numpy as np
import pickle
import collections.abc
import shared_data
import logging
import log

logger = log.setup_custom_logger('TrafficGen')
exec("logger.setLevel(logging.%s)" % (shared_data.logTrafficGen))

# Generate traffic
def trafficGen(id, event):
    logger.info('TrafficGen started')
    b_fin = 0
    t1 = datetime.now()
    while True:
        if shared_data.end_event == True:
            logger.info('TrafficGen ended with success')
            break
        # Genera datos del paquetes
        if shared_data.pkt_len_dist == 'EXP':
            l = int(np.random.exponential(shared_data.pkt_len))
        else:
            l = shared_data.pkt_len
        data = '1' * l
        # Create pkt_ID
        shared_data.pkt_gen += 1
        pkt_id = format(shared_data.pkt_gen, '0' + str(shared_data.IDSIZE) + 'd') 
        # Header
        header = format(l, '0' + str(shared_data.HEADERLENSIZE) + 'd') + pkt_id + str(b_fin) + 'xxxxx' # Data length + id + fin-flag + pkts/serv 
        data = header + data # Header + data
        with shared_data.lock:
            shared_data.buf_len[id] += len(data) # Update app buffer length
            shared_data.cont_paq[id] += 1 # Counter generated packets
        shared_data.q_app[id].put(data) # Send pkt to app buffer
        t2 = datetime.now()
        tt = (t2-t1).total_seconds()
        if shared_data.traf_dist == 'CONT':
            sleep(max(0,(1/shared_data.traf_rate)-tt))
            t1 = datetime.now()
        else: # POISSON
            if(isinstance(shared_data.traf_rate, (collections.abc.Sequence, np.ndarray))):
                e = np.random.exponential(1/shared_data.traf_rate[id])
            else:
                e = np.random.exponential(1/shared_data.traf_rate)
            sleep(max(0, (e-tt)))
            t1 = datetime.now()