'''
Example of plotting the results of the simulation
'''

import os
import sys
from grafColas import grafQ
from grafUtilizacion import grafU
from grafTiempoProc import grafTP
from grafTiempoTotal import grafTT
from grafTiempoProcLong import grafTPL
from grafTiempoTotalLong import grafTTL
from grafColas import grafQ

num_fog = 1
num_cloud = 1
num_proc = 4
num_app = 2
alg = 'Lyapunov'

## Utilization
print('++ Pintando utilización...')
grafU(num_proc)

## Time
print('++ Pintando Tproc...')
grafTP(num_fog, num_proc, num_cloud, num_app)
print('++ Pintando Ttotal...')
grafTT(num_fog, num_proc, num_cloud, num_app)
print('++ Pintando Lserv-Tproc...')
grafTPL(num_fog, num_proc, num_cloud, num_app)
print('++ Pintando Lserv-Ttotal...')
grafTTL(num_fog, num_proc, num_cloud, num_app)

## Queues
print('++ Pintando qApp...')
grafQ('qApp.txt', num_app, 'qApp')
print('++ Pintando qProc...')
grafQ('qProc.txt', num_proc, 'qProc')
if((alg == 'FogCloudLyapunovCostes') or (alg == 'FogCloudLyapunovCostes2')):
    print('++ Pintando G...')
    grafQ('G_lyapunov.txt', num_proc, 'G')
    from grafEstabilidad import grafE
    print('++ Pintando estabilidad G...')
    grafE('G_lyapunov.txt', num_proc, 'Estabilidad G')



