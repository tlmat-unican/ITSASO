##  Autor: Neco Villegas Saiz
##  Universidad de Cantabria    
##  Fecha: 01/06/2022

import os
import sys

print('********** docker kill **********')
os.system ('docker kill $(docker ps -q)')
print('********** docker rm **********')
os.system ('docker rm $(docker ps -a -q)')
print('********** docker network prune **********')
os.system ('docker network prune -f')
try:
    if sys.argv[1] == "-a" or sys.argv[1] == "--all":
        print('********** docker rmi **********')
        os.system('docker rmi $(docker images -q)')
except:
    pass
print('********** docker system prune **********')
os.system('sudo docker system prune -f')
#os.system("sudo rm -r ./Simulaciones/*")