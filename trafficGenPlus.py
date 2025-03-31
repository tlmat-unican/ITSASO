''' Traffic generator (packets)
- CONT 
- POISSON
- LOGNORMAL
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

logger = log.setup_custom_logger('TrafficGen+')
exec("logger.setLevel(logging.%s)" % (shared_data.logTrafficGen))

# Generate traffic
def trafficGen(id, event):
    logger.info('TrafficGen+ started')
    b_fin = 0
    cont = 0
    while True:
        logger.debug('wait ' + str(id))
        event.wait()
        t1 = datetime.now()
        logger.debug('wake up ' + str(id))
        if shared_data.end_event == True:
            logger.info('TrafficGen+ ended with success')
            return
        # Generate number of packets according to the distribution
        if(isinstance(shared_data.traf_rate, (collections.abc.Sequence, np.ndarray))):
            if shared_data.traf_dist == 'LOGNORMAL': num_pkt = np.random.lognormal(shared_data.traf_rate[id], 0.8) # Lognormal(mean, desv)
            if shared_data.traf_dist == 'POISSON': num_pkt = np.random.poisson(shared_data.traf_rate[id]) # Poisson(mean)
            if shared_data.traf_dist == 'CONT': num_pkt = shared_data.traf_rate[id]
        else:
            if shared_data.traf_dist == 'LOGNORMAL': num_pkt = np.random.lognormal(shared_data.traf_rate, 0.8) # Lognormal(media, desv)
            if shared_data.traf_dist == 'POISSON': num_pkt = np.random.poisson(shared_data.traf_rate) # Poisson(media)
            if shared_data.traf_dist == 'CONT': num_pkt = shared_data.traf_rate
        if num_pkt == 0: num_pkt = 1 # At least one packet
        logger.debug('[App ' + str(id) + ', slot ' + str(cont)  + '(' + str(shared_data.serv_gen) + ')] ' + str(num_pkt) + ' pkts' + ' -> ' + str(round(num_pkt)))
        if cont != shared_data.serv_gen:
            logger.warning('[App ' + str(id) + '] trafficGen+(' + str(cont) + ') serviceGen(' + str(shared_data.serv_gen) + ')')
        for i in range(round(num_pkt)):
            if shared_data.end_event == True:
                logger.info('TrafficGen+ ended with success')
                return
            # Generate packet data
            if shared_data.pkt_len_dist == 'EXP':
                l = int(np.random.exponential(shared_data.pkt_len)) # Longitud exponencial negativa
            else:
                l = shared_data.pkt_len
            data = '1' * l
            # Create pkt_ID
            shared_data.pkt_gen += 1
            pkt_id = format(i+1, '0' + str(shared_data.IDSIZE) + 'd') 
            # Header
            header = format(l, '0' + str(shared_data.HEADERLENSIZE) + 'd') + pkt_id + 'c' + str(b_fin) + 'xxxxx' # Data length + id + fin-flag + pkts/serv 
            data = header + data # Header + data
            with shared_data.lock:
                shared_data.buf_len[id] += len(data) # Update app buffer length
                shared_data.cont_paq[id] += 1 # Count packets
            shared_data.q_app[id].put(data) # Put packet in the app buffer 
        logger.debug('clear ' + str(id))
        event.clear()
        t2 = datetime.now()
        logger.warning( '[App ' + str(id) + ', slot ' + str(cont) + ']' + ' t trafficGen ' + str((t2-t1).total_seconds()) + ' sec')
        cont+=1