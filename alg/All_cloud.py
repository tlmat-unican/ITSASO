##  Autor: Neco Villegas Saiz
##  Universidad de Cantabria    
##  Fecha: 20/11/2024

class All_cloud:
    def __init__(self):
        self.node = 'cloud'
    
    def __call__(self, infoNode):

        dic_serv = infoNode['service']['dic_serv'] # Diccionario con los servicios
        for serv_id in dic_serv[1]: # Recorre id de los servicios de una aplicación 1001, 1002... Ahora 1 servicio por aplicación
                if serv_id != 'detailed': # No tiene en cuenta la key detailed, no es un servicio
                    serv_size = dic_serv[1][serv_id]
        for serv_id in dic_serv[1]:
            dic_rt = {1: {serv_id: str(self.node) + '::1::' + str(serv_size)}}
        return dic_rt