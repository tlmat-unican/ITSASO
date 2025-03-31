# Own Libraries
from time import sleep
import gymnasium as gym
import log
import logging
import shared_data
from utils import energy_consumption
from datetime import datetime
import json

logger = log.setup_custom_logger('Basic DPP Algorithm')
logger.setLevel(logging.ERROR)

with open("cnf/conf_DRL_params.json", "r") as jsonfile:
    config = json.load(jsonfile)
PUNISHMENT = config["punishment"]

def write_qProc(f):
    f.write(
        "iot"
        + str(shared_data.sys.argv[2])
        + ","
        + datetime.now().strftime("%H:%M:%S.%f")
        + ","
    )
    for i in range(1, shared_data.iot_num_proc + 1):
        if i != shared_data.iot_num_proc:
            f.write(str(shared_data.iot_dic_processor["q_" + str(i)].qsize()) + ",")
        else:
            f.write(str(shared_data.iot_dic_processor["q_" + str(i)].qsize()) + "\n")


class IoTTaskOffloadingEnv(gym.Env):
    def __init__(self):
        super(IoTTaskOffloadingEnv, self).__init__()
        # Action space: 3 discrete actions (e.g., Offload to cloud, fog, or process locally)
        self.n_discrete_actions = 3
        self.action_space = gym.spaces.Discrete(self.n_discrete_actions)
        
        
        # # # Define observation space with discrete ranges
        self.n_features = 5
        self.observation_space = gym.spaces.MultiDiscrete([
            2,    # channel_quality (0 or 1)
            101,  # queue_iot (0 to 100)
            101,  # queue_fog (0 to 100)
            1001, # service_length (0 to 1000)
            1001  # delay_request (0 to 1000)
        ])
        
        # Additional variables (e.g., cloud queue, service ID, etc.)
        self.battery: int
        self.queue_cloud = 0
        self.serv_id = None
        self.serv_time = None

    def step(
        self,
        app_id,
        delay,
        serv_id,
        dic_request,
        serv_len,
        f2,
        f3,
        logger,
        fog_sock,
        s,
        d_req
    ):

        if self.serv_id is not None:
            self.serv_time= self.update_G()

        done = False
        
        self.serv_id = serv_id
        self.channel_quality = delay
        self.queue_iot = dic_request['iot']['proc1']['q_len'] # IoT processor queue state
        self.queue_fog = dic_request['fog'][0]['proc1']['q_len'] # Fog processor queue state
        previous_battery = self.battery
        self.delay_request = d_req
        
        total_serv_len = 0
        
        s = s.split("::") 
        self.service_length = s[2]
        if (len(s) == 2): # If there are only two elements (e.g., local::1), it means the service size has been omitted and needs to be included
            s.append(serv_len[app_id - 1])
        if s[2] == "0":
            logger.debug("0 pkts to process. Service skipped")
            return (
                [0,0,0,0,0],
                0,
                False,
                s,
                total_serv_len
            )

        if s[0] == "local":
            logger.debug("It was chosen to process locally (IoT) using processor" + str(s[1]))
            # For all the packets in the input buffer at the moment of the service arrival
            for p in range(int(s[2])):
                # Get packet from the buffer
                pkt = shared_data.q_app[app_id - 1].get()
                with shared_data.lock:
                    # Update the buffer length
                    shared_data.buf_len[app_id - 1] -= len(pkt)
                pkt = (
                    pkt[
                        : shared_data.HEADERLENSIZE
                        + shared_data.IDSIZE
                        + 1
                        + 1
                        + shared_data.PKTSERLEN
                    ]
                    + format(serv_id, "05d") # NOTE serv_id has 5 digits
                    + pkt[
                        shared_data.HEADERLENSIZE
                        + shared_data.IDSIZE
                        + 1
                        + 1
                        + shared_data.PKTSERLEN
                        + shared_data.LENSEV :
                    ]
                )  # They will not be sent. pkts/serv is not necessary. Only serv_id
                # The service is added to the local queue
                shared_data.iot_dic_processor["q_" + str(s[1])].put(pkt)
                with shared_data.lock: # Update the size of the local queue
                    shared_data.q_len[int(s[1]) - 1] += len(pkt)
            # Indicates that there is a complete service of 'serv_len' packets to process
            shared_data.iot_dic_processor["q_proc_" + str(s[1])].put(int(s[2]))
            f2.write(
                str(shared_data.serv_gen)
                + ","
                + datetime.now().strftime("%H:%M:%S.%f")
                + ","
                + str(s[0])
                + "::"
                + str(s[1])
                + "::"
                + str(s[2])
                + ","
                + "iot"
                + str(shared_data.sys.argv[2])
                + "\n"
            )
            write_qProc(f3)
            # Wake up the corresponding processor
            shared_data.iot_dic_processor["event_" + str(s[1])].set()
            logger.debug(
                "Service of "
                + str(serv_len)
                + " pkts, buffer = "
                + str(shared_data.q_app[app_id - 1].qsize())
                + " pkts"
            )
        # Send the service (complete or partial) to the assigned Fog node
        elif s[0] == "fog":
            logger.debug("It was chosen to process remotely (Fog" + str(s[1]) + ")")
            sock_index = int(s[1]) - 1
            # Number of packets in the service
            num_pkts_serv = int(s[2])
            # In the first packet of the service, the total number of packets sent in this service (complete or partial) is indicated
            # Retrieve the packet
            pkt = shared_data.q_app[app_id - 1].get()
            with shared_data.lock:
                # Update the input buffer length
                shared_data.buf_len[app_id - 1] -= len(pkt)
            # Add the total number of packets in the service and the corresponding serv_id to the header
            pkt = (
                pkt[: shared_data.HEADERLENSIZE + shared_data.IDSIZE]
                + "0"
                + "0"
                + format(
                    num_pkts_serv,
                    "0" + str(shared_data.PKTSERLEN) + "d",
                )
                + format(serv_id, "05d")
                + pkt[
                    shared_data.HEADERLENSIZE
                    + shared_data.IDSIZE
                    + shared_data.PKTSERLEN
                    + 1
                    + 1 :
                ]
            )
            # Same for the rest of the packets in the service, but without including the number of packets per service. It remains as 'xxxx'
            f2.write(
                str(shared_data.serv_gen)
                + ","
                + datetime.now().strftime("%H:%M:%S.%f")
                + ","
                + str(s[0])
                + "::"
                + str(s[1])
                + "::"
                + str(num_pkts_serv)
                + ","
                + "iot"
                + str(shared_data.sys.argv[2])
                + "\n"
            )
            for i in range(num_pkts_serv):
                if i == 0:
                    pkt_1 = pkt
                if i == 1:
                    paquetes = pkt.encode()
                    logger.debug(f'paquetes = {paquetes}')
                if i > 1:
                    paquetes += pkt.encode()
                    logger.debug(f'Add to packets {pkt.encode()}')
                if i == (num_pkts_serv - 1):
                    pass
                else:
                    pkt = shared_data.q_app[app_id - 1].get()
                    with shared_data.lock:
                        shared_data.buf_len[app_id - 1] -= len(pkt)
                    pkt = (
                        pkt[
                            : shared_data.HEADERLENSIZE
                            + shared_data.IDSIZE
                            + shared_data.PKTSERLEN
                            + 1
                            + 1
                        ]
                        + format(serv_id, "05d") # NOTE serv_id has 5 digits
                        + pkt[
                            shared_data.HEADERLENSIZE
                            + shared_data.IDSIZE
                            + shared_data.PKTSERLEN
                            + 1
                            + 1 :
                        ]
                    )
            if fog_sock[sock_index].fileno() != -1:
                pkt_1 = pkt_1.encode()
                if num_pkts_serv == 1:
                    fog_sock[sock_index].sendall(pkt_1)
                    sleep(delay/1000)
                else:
                    fog_sock[sock_index].sendall(pkt_1 + paquetes)
                    sleep(delay/1000)
        # Send the service (complete or partial) to the assigned Cloud node
        elif s[0] == "cloud":
            logger.debug("It was chosen to process remotely (Cloud" + str(s[1]) + ")")
            sock_index = int(s[1]) - 1
            # Number of packets in the service
            num_pkts_serv = int(s[2])
            # In the first packet of the service, indicate the total number of packets being sent in this service (complete or partial)
            # Get the packet
            pkt = shared_data.q_app[app_id - 1].get()
            with shared_data.lock:
                # Updates input buffer size
                shared_data.buf_len[app_id - 1] -= len(pkt)
            # Adds the total number of pkts in the service and the corresponding serv_id to the header
            # The same for the rest of the pkts in the service, but without including the number of pkts per service. It remains as 'xxxx'
            pkt = (
                pkt[: shared_data.HEADERLENSIZE + shared_data.IDSIZE]
                + "1"
                + "0"
                + format(
                    num_pkts_serv,
                    "0" + str(shared_data.PKTSERLEN) + "d",
                )
                + format(serv_id, "05d")
                + pkt[
                    shared_data.HEADERLENSIZE
                    + shared_data.IDSIZE
                    + shared_data.PKTSERLEN
                    + 1
                    + 1 :
                ]
            )
            f2.write(
                str(shared_data.serv_gen)
                + ","
                + datetime.now().strftime("%H:%M:%S.%f")
                + ","
                + str(s[0])
                + "::"
                + str(s[1])
                + "::"
                + str(s[2])
                + ","
                + "iot"
                + str(shared_data.sys.argv[2])
                + "\n"
            )
            for i in range(num_pkts_serv):
                try:
                    if fog_sock[sock_index].fileno() != -1:
                        logger.debug("pkt = " + str(pkt))
                        if i == 0:
                            pkt_1 = pkt.encode()
                        elif i == 1:
                            paquetes = pkt.encode()
                            logger.debug(f'paquetes = {paquetes}')
                        else:
                            paquetes += pkt.encode()
                            logger.debug(f'Add to packets {pkt.encode()}')
                except ValueError:
                    problem = s
                    logger.error("fog_sock is closed")
                    break
                except BrokenPipeError:
                    logger.error("Broken pipe error")
                    break
                except ConnectionResetError:
                    logger.error("Connection reset error")
                    break
                    
                # The first packet is already prepared, skip the first iteration
                if i == (num_pkts_serv - 1):
                    pass
                else:
                    pkt = shared_data.q_app[app_id - 1].get()
                    with shared_data.lock:
                        shared_data.buf_len[app_id - 1] -= len(pkt)
                    pkt = (
                        pkt[
                            : shared_data.HEADERLENSIZE
                            + shared_data.IDSIZE
                            + 1
                            + 1
                            + shared_data.PKTSERLEN
                        ]
                        + format(serv_id, "05d") # NOTE amplio a 5 digitos el serv_id
                        + pkt[
                            shared_data.HEADERLENSIZE
                            + shared_data.IDSIZE
                            + 1
                            + 1
                            + shared_data.PKTSERLEN :
                        ]
                    )
                    pkt = (
                        pkt[
                            : shared_data.HEADERLENSIZE
                            + shared_data.IDSIZE
                        ]
                        + "1"
                        + "0"
                        + pkt[
                            shared_data.HEADERLENSIZE
                            + shared_data.IDSIZE
                            + 1
                            + 1 :
                        ]
                    )
            if fog_sock[sock_index].fileno() != -1:
                if num_pkts_serv == 1:
                    logger.critical(f'envio paquete a Fog (hacia cloud)')
                    fog_sock[sock_index].sendall(pkt_1)
                    sleep(delay/1000)
                else:
                    logger.critical(f'+++ envio todos los paquetes a Fog (hacia Cloud) de golpe {pkt_1+paquetes}')
                    fog_sock[sock_index].sendall(pkt_1 + paquetes)
                    sleep(delay/1000)
        if s != "":
            self.battery = energy_consumption(shared_data.bateria, s[0], delay,num_pkts=int(s[2]))
            shared_data.bateria=self.battery
            
            total_serv_len += int(s[2])
            self.service_length = total_serv_len
            if self.serv_time==None:
                reward = PUNISHMENT
            elif self.serv_time>self.delay_request:
                reward = PUNISHMENT
            else:
                reward = self.battery - previous_battery

            self.queue_iot = shared_data.iot_dic_processor["q_1"].qsize()
            self.queue_fog = shared_data.fogInfo[0].get('proc1', {}).get('q_len', 0) if shared_data.fogInfo else 0

            next_state = [
                self.channel_quality,
                self.queue_iot,
                self.queue_fog,
                self.service_length,
                self.delay_request,
            ]
            
            logger.debug(f"action={s}, reward={reward}, next_state={next_state}")
            return (
                next_state,
                reward,
                done,
                s,
                total_serv_len
            )
        else:
            next_state = [
                self.channel_quality,
                self.queue_iot,
                self.queue_fog,
                self.service_length,
                self.delay_request,
                total_serv_len
            ]
            reward = PUNISHMENT 
            done = False
            logger.debug(f"action={s}, reward={reward}, next_state={next_state}")
            return (
                next_state,
                reward,
                done,
                s,
                total_serv_len
            )

    def update_G(self):
        if self.serv_id not in shared_data.serv_time_results: # Esto significaría que el servicio no ha sido procesado desde la decisión anterior, lo cual no debería ocurrir. Si pasa actualizo G con un delay de 1 segundo por poner algo
            self.serv_time = 1000
        else:
            self.serv_time = float(shared_data.serv_time_results[self.serv_id])
        return self.serv_time
            
    def _allocate_local(self, app, serv_id, pkts):
        s = ""
        pkts_proc = pkts  # NOTE revisar
        self.queue_iot += pkts_proc
        s += "local::" + str(1) + "::" + str(int(pkts))
        pkts = 0
        return s, pkts

    def _allocate_fog(self, app, serv_id, pkts):
        s = ""
        pkts_proc = pkts
        self.queue_fog += pkts_proc
        s += "fog::1::" + str(int(pkts_proc))
        pkts = 0
        return s, pkts

    def _allocate_cloud(self, app, serv_id, pkts):
        s = ""
        pkts_proc = pkts
        self.queue_cloud += pkts_proc
        s += "cloud::1::" + str(int(pkts_proc))
        pkts = 0
        return s, pkts

    def reset(self):
        # Reset the environment to an initial state and return the initial observation
        # Diccionario con los servicios {1: {1002: 5, 1001: 1}, 2: {2002: 4}, 3: {3002: 5}}

        # Space variables
        self.battery = 100
        self.channel_quality = 0
        # self.queue_iot = np.zeros(self.num_iot_processors)
        self.queue_iot = 0  # NOTE change if more processors
        self.queue_fog = 0
        # self.queue_fog = np.zeros((self.num_fog_processors, len(self.dic_serv)))
        # self.queue_fog = np.zeros(self.num_fog_processors)#, len(self.dic_serv)))
        self.service_length = 0
        self.delay_request = 0

        return [
            self.channel_quality,
            self.queue_iot,
            self.queue_fog,
            self.service_length,
            self.delay_request
        ]

    def render(self, mode="human"):
        # Optional: print or visualize the environment's state
        pass
