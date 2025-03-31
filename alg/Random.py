##  Autor: Neco Villegas Saiz
##  Universidad de Cantabria    
##  Fecha: 04/12/2024

from distutils.log import INFO
import logging
from random import randint
import numpy as np
from itertools import product
import log
logger = log.setup_custom_logger('Basic DPP Algorithm')
logger.setLevel(logging.ERROR) # (logging.DEBUG)

class Random:
    def __init__(self):
        pass
    
    def __call__(self, infoNode):

        dic_serv = infoNode['service']['dic_serv'] # Diccionario con los servicios
        for serv_id in dic_serv[1]: # Recorre id de los servicios de una aplicación 1001, 1002... Ahora 1 servicio por aplicación
                if serv_id != 'detailed': # No tiene en cuenta la key detailed, no es un servicio
                    serv_size = dic_serv[1][serv_id]
        node = ['local', 'fog', 'cloud']
        i = randint(0, 2)
        # i= 1
        for serv_id in dic_serv[1]:
            dic_rt = {1: {serv_id: str(node[i]) + '::1::' + str(serv_size)}}
        logger.debug(f"Random -> dic_rt: {dic_rt}")
        return dic_rt # {1: {1059: 'local::1::1'}}