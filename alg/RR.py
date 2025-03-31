##  Autor: Neco Villegas Saiz
##  Universidad de Cantabria    
##  Fecha: 20/11/2024

from distutils.log import INFO
import logging
from random import randint
import numpy as np
from itertools import product
import log
logger = log.setup_custom_logger('Basic DPP Algorithm')
logger.setLevel(logging.CRITICAL) # (logging.DEBUG)

class RR:
    def __init__(self):
        self.prio = 0

    def select_prio(self, num_max):
        self.prio += 1
        if self.prio > num_max:
            self.prio = 0
    
    def __call__(self, infoNode):

        dic_serv = infoNode['service']['dic_serv'] # Diccionario con los servicios
        for serv_id in dic_serv[1]: # Recorre id de los servicios de una aplicación 1001, 1002... Ahora 1 servicio por aplicación
                if serv_id != 'detailed': # No tiene en cuenta la key detailed, no es un servicio
                    serv_size = dic_serv[1][serv_id]
        node = ['local', 'fog', 'cloud']
        self.select_prio(2)
        for serv_id in dic_serv[1]:
            dic_rt = {1: {serv_id: str(node[self.prio]) + '::1::' + str(serv_size)}}
        logger.debug(f"RR -> dic_rt: {dic_rt}")
        return dic_rt # {1: {1059: 'local::1::1'}}