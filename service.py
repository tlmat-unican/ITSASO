""" Service generator.
Also handles communication with the offloading algorithm and the subsequent
distribution of services to local processors or Fog/Cloud nodes.
"""

from time import sleep
from datetime import datetime
import os
import numpy as np
import pickle
import shared_data
import logging
import log
from alg.environment_DRL import IoTTaskOffloadingEnv
from utils import energy_consumption
import importlib
import multiprocessing
from pyroute2 import IPRoute
import threading
import csv
import json
import re

logger = log.setup_custom_logger("Service")
exec("logger.setLevel(logging.%s)" % (shared_data.logService))

with open("cnf/conf_DRL_params.json", "r") as jsonfile:
    config = json.load(jsonfile)
PUNISHMENT = config["punishment"]

if shared_data.alg_name != "ActorCriticAgent" and shared_data.alg_name != "ActorCriticAgent_no_tf" and shared_data.alg_name != "PPO" and shared_data.alg_name !="DRL_random":
    try:
        mod = importlib.import_module("alg." + shared_data.alg_name)
    except ImportError:
        logger.error(f"Module 'alg.{shared_data.alg_name}' could not be imported.")
        mod = importlib.import_module(f'alg.{shared_data.alg_name}')

p_tx = 0.5
k = 1e-23

load_model= False
save_model = True
re_train=True

def calculate_slot_serv():
    # CONT: in slots of duration slot_time
    # POISSON: exponential time between service generations
    if shared_data.serv_dist == "CONT":
        return shared_data.slot_time
    else:
        return np.random.exponential(1 / shared_data.serv_rate)
    

def read_csv_row(filename, x):
    row_data = []
    with open(filename, 'r') as file:
        reader = csv.reader(file)
        for i, row in enumerate(reader):
            if i == x - 1:
                row_data = [int(value) for value in row]
                break
    return row_data

# Service generation
def service(id):
    logger.debug("Service generator started")
    global serv_event, pkt_sent
    f = open("./res/" + "iotServicesGen.txt", "a+")
    f2 = open("./res/" + "iotAssigment.txt", "a+")
    f3 = open("./res/" + "iotQProc.txt", "a+")
    f4 = open("./res/" + "qApp.txt", "a+")
    f5 = open("./res/" + "reg.txt", "a+")
    f6 = open("./res/" + "iotBatt_" + str(id) + ".txt", "a+")
    f7 = open("./res/" + "iotReward.txt", "a+")
    f8 = open("./res/" + "losses.txt", "a+")
    t1 = datetime.now()

    socket_lock = threading.Lock()
    threading.Thread(target=handle_fog_messages, args=(socket_lock,)).start()
    
    array_delay = read_csv_row("cnf/delay_requirements.csv", int(shared_data.sys.argv[2]))

    reg = {}
    rq = {}
    # Initialize the dictionary with the application keys
    for i in range(shared_data.num_app):
        rq[i + 1] = {}
        reg[i + 1] = {}
    cont = 0
    # with socket_lock:
    try:
        fog_control_sock.send(str(id).encode())
        logger.debug(f"Sended id {id} to FogControl")
    except:
        logger.error("Error sending InfoRq con id to FogControl")

    wakeup_trafficGen() # Wakes up the traffic generators (applications)
    sleep(2)

    if (
        shared_data.alg_name == "ActorCriticAgent"
        or shared_data.alg_name == "ActorCriticAgent_no_tf"
        or shared_data.alg_name == "DQN"
        or shared_data.alg_name == "q_learning"
        or shared_data.alg_name == "DRL_random"
        or shared_data.alg_name == "PPO"
    ):
        iotInfo = collect_info()
        # Service information
            # Number of packets that make up the service
            # Service ID
            # Number of stages (kept in case it's used in the future)
        servInfo = {
            "dic_serv": rq,
            "num_slot": shared_data.serv_gen,
            "num_app": shared_data.num_app,
            "p_len": shared_data.pkt_len,
            "t_slot": shared_data.slot_time,
        }
        # Gather all the information to be sent to the offloading algorithm
        dic_request = {
            "service": servInfo,
            "iot": iotInfo,
            "fog": shared_data.fogInfo if shared_data.fogInfo else [{"proc1": {"q_len": 0}}], # 0 por si no llega report del fog
            "clouds": shared_data.cloudInfo,
        }
        env = IoTTaskOffloadingEnv()
        state = env.reset()

        n_actions = 3  # NOTE: To consider x processors and fog nodes, this needs to be updated

        if shared_data.alg_name == "DQN":
            parent_conn, child_conn = multiprocessing.Pipe()
            p = multiprocessing.Process(target=agent_process_DQN, args=(child_conn,))
            p.start()
            
            if load_model: 
                parent_conn.send(
                    {
                        "command": "load_model",
                        "data": str(id),
                    }
                )
                load_status = parent_conn.recv()
                logger.debug(load_status)
        
        elif shared_data.alg_name == "q_learning":
            parent_conn, child_conn = multiprocessing.Pipe()
            p = multiprocessing.Process(target=agent_process_QLearning, args=(child_conn,))
            p.start()
            
            if load_model: 
                parent_conn.send(
                    {
                        "command": "load_model",
                        "data": str(id),
                    }
                )
                load_status = parent_conn.recv()
                logger.debug(load_status)
        
        elif shared_data.alg_name == "ActorCriticAgent":
            parent_conn, child_conn = multiprocessing.Pipe()
            p = multiprocessing.Process(target=agent_process, args=(child_conn,))
            p.start()
            actor_losses = []
            critic_losses = []
            if load_model:
                parent_conn.send({"command": "load_model", "data": str(id)})
                load_status = parent_conn.recv()
                logger.debug(load_status)
                # alg.load_model(str(id))
        
        elif shared_data.alg_name == "ActorCriticAgent_no_tf":
            parent_conn, child_conn = multiprocessing.Pipe()
            p = multiprocessing.Process(target=agent_process_no_tf, args=(child_conn,))
            p.start()
            actor_losses = []
            critic_losses = []
            if load_model:
                parent_conn.send({"command": "load_model", "data": str(id)})
                load_status = parent_conn.recv()
                logger.debug(load_status)
                # alg.load_model(str(id))
            
        elif shared_data.alg_name == "PPO":
            parent_conn, child_conn = multiprocessing.Pipe()
            p = multiprocessing.Process(target=agent_process_PPO, args=(child_conn,))
            p.start()
            actor_losses = []
            critic_losses = []
            if load_model:
                parent_conn.send({"command": "load_model", "data": str(id)})
                load_status = parent_conn.recv()
                logger.debug(load_status)
        
        else:
            parent_conn, child_conn = multiprocessing.Pipe()
            p = multiprocessing.Process(target=agent_process_DRL_random, args=(child_conn,))
            p.start()
    else:
        alg = eval("mod." + shared_data.alg_name + "()")
    
    done = False
    prev_state=None
    prev_reward=None
    prev_action=None
    battery_prev = shared_data.battery
    while True:
        if shared_data.serv_gen > 0:
            try:
                os.system("tc qdisc del dev eth0 root")
            except:
                pass
        try:
            delay_index = shared_data.serv_gen % len(shared_data.delay[int(id)-1])
            delay = int(shared_data.delay[int(id)-1][delay_index])
            logger.debug(
                f"{shared_data.serv_gen} - tc qdisc add dev eth0 root netem delay {delay}ms"
            )
            os.system(f"tc qdisc add dev eth0 root netem delay {delay}ms")
        except:
            logger.error("csv is not large enough")
        # Gather all the information to be sent to the offloading algorithm
            # Information from Cloud and Fog nodes
            # Collect data from all Cloud nodes
        shared_data.cloudInfo = []
        # Send InfoRq periodically in a new thread
        threading.Thread(target=send_info_request, args=(fog_control_sock, 0, socket_lock,)).start()
        # Track queue state periodically
        write_qProc(f3)
        e = calculate_slot_serv()
        t2 = datetime.now()
        tt = (t2 - t1).total_seconds()
        logger.debug(
            "[slot "
            + str(shared_data.serv_gen)
            + "] e = "
            + str(e)
            + ", tt = "
            + str(tt)
            + " sleep("
            + str(max(0.1, (e - tt)))
            + ")"
        )
        if shared_data.serv_gen > 0:
            wakeup_trafficGen() # Wake up the traffic generators (applications)
            sleep(max(0.1, (e - tt)))
            prev_reward = calc_reward(shared_data.serv_gen-1 + ((id) * 1000), dic_request, battery_prev, f7,d_req)
        
        t1 = datetime.now()
        logger.debug(
            "* Slot "
            + str(shared_data.serv_gen)
            + " lasted "
            + str(max(e, tt))
            + " sec."
        )
        cont += max(0, (e - tt))
        logger.debug("Total duration of all slots " + str(cont) + " sec.")
        f4.write(
            "iot"
            + str(shared_data.sys.argv[2])
            + ","
            + datetime.now().strftime("%H:%M:%S.%f")
            + ","
        )
        for buf in shared_data.q_app:
            if buf != shared_data.q_app[-1]:
                f4.write(str(buf.qsize()) + ",")
        f4.write(str(buf.qsize()) + "\n")

        if shared_data.end_event == True:
            logger.info("Service generator ended with success")
            f.close()
            f2.close()
            f3.close()
            f4.close()
            f5.close()
            f6.close()
            f7.close()
            f8.close()
            wakeup_trafficGen()
            break
        serv_len = calc_buf_size()
        if shared_data.serv_gen > 0:
            for a in rq:
                pkts_pend = 0
                for s in rq[a]:
                    pkts_pend += rq[a][s]
                serv_len[a - 1] = serv_len[a - 1] - pkts_pend
        logger.debug("New service, serv_len = " + str(serv_len))
        # Create the dictionary to be sent to the offloading algorithm. It has the following structure:
        # {1: {1002: 9, 1001: 1, detailed: {buf_size, etc}}, 2: {2002: 9}, 3: {3002: 9}}
        app_id = list(range(1, shared_data.num_app + 1))
        # Add new services (those from the current slot) to rq
        for i in range(1, shared_data.num_app + 1):
            rq[i].update(
                {shared_data.serv_gen + ((id) * 1000): serv_len[i - 1]} # NOTE: I'm going to identify IoT nodes by the first two digits of the serv_id
            )
        logger.debug("rq_f = " + str(rq))
        f.write(
            str(shared_data.serv_gen + ((id) * 1000))
            + ","
            + t1.strftime("%H:%M:%S.%f")
            + ","
            + "iot"
            + str(shared_data.sys.argv[2])
            + "\n"
        )  # Time when the service is generated

        # Save the time when the service was generated to calculate the total time until it is processed
        shared_data.services_gen[shared_data.serv_gen + ((id) * 1000)] = t1.strftime("%H:%M:%S.%f")

        # Information about the processors of the IoT node
        iotInfo = collect_info()
        # Service information
        if shared_data.serv_delay_req[0]== -1:
            d_req=array_delay[shared_data.serv_gen]
        else:
            d_req=shared_data.serv_delay_req[0] 
        servInfo = {
            "dic_serv": rq,
            "num_slot": shared_data.serv_gen,
            "num_app": shared_data.num_app,
            "p_len": shared_data.pkt_len,
            "t_slot": shared_data.slot_time,
            "delay_req": d_req,
        }
        # Gather all the information to be sent to the offloading algorithm
        dic_request = {
            "service": servInfo,
            "iot": iotInfo,
            "fog": shared_data.fogInfo if shared_data.fogInfo else [{"proc1": {"q_len": 0}}], # 0 in case the report from the fog does not arrive on time
            "clouds": shared_data.cloudInfo,
            "delay_iot_fog": int(delay),
            "delay_fog_cloud": shared_data.delay_fog_cloud,
        }
        
        # Send the information to the offloading algorithm
        for app_id in range(1, shared_data.num_app + 1):
            # I store a record of ALL the services (needed for the calculation of pending packets)
            reg[app_id].update(rq[app_id])
        rq = {}  # Clears the dictionary to create it from scratch for the next slot
        # Initializes the dictionary with the keys of the applications
        for i in range(shared_data.num_app):
            rq[i + 1] = {}
        # Receives the response
        # It is a dictionary with the location where to process the services:
        # {1: {1002: 'local::1', 1001: 'local::2'}, 2: {2002: 'local::3'::2}, 3: {3002: 'local::4'}}
        logger.debug('Sended "' + str(dic_request) + '" to offloading algorithm')
        if (
            shared_data.alg_name == "ActorCriticAgent"
            or shared_data.alg_name == "ActorCriticAgent_no_tf"
            or shared_data.alg_name == "DQN"
            or shared_data.alg_name == "q_learning"
            or shared_data.alg_name == "DRL_random"
            or shared_data.alg_name == "PPO"
        ):
            dic_serv_g = dic_request['service']['dic_serv']
            for serv_id in dic_serv_g[1]:
                if serv_id != 'detailed':
                    serv_size = dic_serv_g[1][serv_id]
                    if shared_data.serv_delay_req[0]== -1:
                        d_req=array_delay[shared_data.serv_gen]
                    else:
                        d_req=shared_data.serv_delay_req[0] 
            state = [int(delay),
                        dic_request["iot"]["proc1"]["q_len"],
                        dic_request["fog"][0]["proc1"]["q_len"],
                        serv_size,
                        d_req]
            logger.debug(f"State: {state}")
            
            t_ini=datetime.now()
            # Choose action
            if shared_data.alg_name == "ActorCriticAgent" or shared_data.alg_name == "ActorCriticAgent_no_tf" or shared_data.alg_name == "DQN" or shared_data.alg_name == "DRL_random" or shared_data.alg_name == "PPO":
                parent_conn.send({"command": "choose_action", "data": state})
                action, log_prob = parent_conn.recv()
            
            elif shared_data.alg_name == "q_learning":
                parent_conn.send({"command": "choose_action", "data": state})
                action = parent_conn.recv()
            else:
                action, log_prob = alg.choose_action(state)
            
            logger.debug(
                        f"Time to take an action: {(datetime.now()-t_ini).total_seconds()}",
                    )
            logger.debug(f"Action: {action}")
            
            # Generate master_recv_dic
            if action==0:
                master_recv_dic = {1: {serv_id:"local::1::" + str(serv_size)}}
            elif action==1:
                master_recv_dic = {1: {serv_id:"fog::1::" + str(serv_size)}}
            elif action==2:
                master_recv_dic = {1: {serv_id:"cloud::1::" + str(serv_size)}}
            
            # Iterate over the array
            for app_id in master_recv_dic:
                total_app_len = 0
                for serv_id in master_recv_dic[app_id]:  # 1002 1001...
                    t_ini=datetime.now()
                    total_serv_len = 0
                    services = master_recv_dic[app_id][serv_id].split(
                        ","
                    )
                    battery_prev = shared_data.battery
                    for s in services:
                        (next_state,reward,done,s,total_serv_len) = env.step(app_id,int(delay),serv_id,dic_request,serv_len,f2,f3,logger,fog_sock,s,d_req)
                    t_ini = datetime.now()
                    prev_state = state
                    state = next_state
                    
                    reg[app_id][serv_id] = reg[app_id][serv_id] - total_serv_len

                    total_app_len += total_serv_len
                    
            logger.debug("***** " + str(shared_data.serv_gen) + " *****")
            for a in reg:
                for s in reg[a]:
                    # Services with packets to process
                    if s != "detailed" and reg[a][s] != 0:
                        logger.debug("update rq -> " + str(s) + ": " + str(reg[a][s]))
                        rq[a].update({s: reg[a][s]})
                    else:
                        pass
                        logger.debug(
                            "no update rq -> " + str(s) + ": " + str(reg[a][s])
                        )
            logger.debug("Sumo 1 a serv_gen")
            # Counter for services generated by application. It matches the number of slots. Used to build the serv_id
            shared_data.serv_gen += 1
            f4.write(
                "iot"
                + str(shared_data.sys.argv[2])
                + ","
                + datetime.now().strftime("%H:%M:%S.%f")
                + ","
            )
            for buf in shared_data.q_app:
                if buf != shared_data.q_app[-1]:
                    f4.write(str(buf.qsize()) + ",")
            f4.write(str(buf.qsize()) + "\n")

            f6.write(
                        "iot"
                        + str(shared_data.sys.argv[2])
                        + ","
                        + str(shared_data.serv_gen)
                        + ","
                        + datetime.now().strftime("%H:%M:%S.%f")
                        + ","
                        + str(shared_data.battery)
                        + "\n"
                    )

            if prev_action is not None and re_train:
                logger.debug("Update model with reward "+ str(prev_reward))
                t_ini=datetime.now()
                if shared_data.alg_name == "DQN":
                    parent_conn.send(
                        {
                            "command": "update",
                            "data": (prev_state, prev_action, prev_reward, state, done),
                        }
                    )
                    update_status = parent_conn.recv()
                    logger.debug("Received loss "+ str(update_status))
                    loss = update_status.numpy()
                    f8.write(
                        "iot"
                        + str(shared_data.sys.argv[2])
                        + ","
                        + str(shared_data.serv_gen)
                        + ","
                        + str(loss)
                        + "\n"
                    )

                elif shared_data.alg_name == "q_learning":
                    parent_conn.send(
                        {
                            "command": "update",
                            "data": (prev_state, prev_reward, state, done,prev_action),
                        }
                    )
                
                elif shared_data.alg_name == "ActorCriticAgent" or shared_data.alg_name == "ActorCriticAgent_no_tf":
                    parent_conn.send(
                        {
                            "command": "update",
                            "data": (prev_state, prev_reward, state, done, log_prob,prev_action),
                        }
                    )
                    update_status = parent_conn.recv()
                    logger.info("Update Status: "+ str(update_status))
                    actor_loss, critic_loss = update_status
                    #actor_loss = actor_loss.numpy()
                    #critic_loss = critic_loss.numpy()
                    actor_loss = float(actor_loss[0][0])
                    critic_loss = float(critic_loss[0][0])
                    f8.write(
                        "iot"
                        + str(shared_data.sys.argv[2])
                        + ","
                        + str(shared_data.serv_gen)
                        + ","
                        + str(actor_loss)
                        + ","
                        + str(critic_loss)
                        + "\n"
                    )
                    
                elif shared_data.alg_name == "PPO":
                    parent_conn.send(
                        {
                            "command": "update",
                            "data": (prev_state, prev_reward, state, done, log_prob,prev_action),
                        }
                    )
                    update_status = parent_conn.recv()
                    logger.debug("Update Status: "+ str(update_status))
                    if update_status is not None:
                        actor_loss, critic_loss = update_status
                        actor_loss = float(actor_loss)
                        critic_loss = float(critic_loss)
                        f8.write(
                            "iot"
                            + str(shared_data.sys.argv[2])
                            + ","
                            + str(shared_data.serv_gen)
                            + ","
                            + str(actor_loss)
                            + ","
                            + str(critic_loss)
                            + "\n"
                        )
                        
                else:
                    a=0
                
            prev_action = action

        # Control Theory algorithms
        else:
            t_ini=datetime.now()
            master_recv_dic = alg(dic_request)
            for app_id in master_recv_dic:  # 1
                total_app_len = 0
                for serv_id in master_recv_dic[app_id]:  # 1002 1001...
                    if serv_id != 'detailed':
                        serv_size = master_recv_dic[1][serv_id]
                        if shared_data.serv_delay_req[0]== -1:
                            d_req=array_delay[shared_data.serv_gen]
                        else:
                            d_req=shared_data.serv_delay_req[0] 
                    t_ini=datetime.now()
                    total_serv_len = 0
                    services = master_recv_dic[app_id][serv_id].split(
                        ","
                    )  # ['local::1::9', 'local::2::1']
                    for s in services:  # 'local::1::9'
                        s = s.split("::")  # ['local', '1', '9']
                        if (
                            len(s) == 2
                        ):  # If there are only two elements (e.g., local::1), it means the service size was omitted and needs to be included
                            s.append(serv_len[app_id - 1])

                        if s[2] == "0":
                            logger.debug("0 pkts to process. Service skipped")
                            break  # If the service size is 0, it is not sent
                        if s[0] == "local": # Refers to processors of the IoT node
                            logger.debug(
                                "It was chosen to process locally (IoT) using processor"
                                + str(s[1])
                            )
                            # For all packets in the input buffer at the time the service arrives
                            for p in range(int(s[2])):
                                # They are removed from the buffer
                                pkt = shared_data.q_app[app_id - 1].get()
                                with shared_data.lock:
                                    # The buffer length is updated
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
                                ) 
                                shared_data.iot_dic_processor["q_" + str(s[1])].put(
                                    pkt
                                )
                                with shared_data.lock: # update local queue size
                                    shared_data.q_len[int(s[1]) - 1] += len(pkt)
                            # Indicates that there is a complete service of 'serv_len' pkts to process
                            shared_data.iot_dic_processor["q_proc_" + str(s[1])].put(
                                int(s[2])
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
                            logger.debug(
                                "It was chosen to process remotely (Fog"
                                + str(s[1])
                                + ")"
                            )
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
                                + "0"
                                + "0"
                                + format(
                                    num_pkts_serv,
                                    "0" + str(shared_data.PKTSERLEN) + "d",
                                )
                                + format(serv_id, "05d") # NOTE serv_id has 5 digits
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
                            logger.debug(
                                "It was chosen to process remotely (Cloud"
                                + str(s[1])
                                + ")"
                            )
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
                                + format(serv_id, "05d") # NOTE serv_id has 5 digits
                                + pkt[
                                    shared_data.HEADERLENSIZE
                                    + shared_data.IDSIZE
                                    + shared_data.PKTSERLEN
                                    + 1
                                    + 1 :
                                ]
                            )
                            logger.debug(
                                "PKTSERLEN = " + format(num_pkts_serv),
                                "0" + str(shared_data.PKTSERLEN) + "d",
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
                                        if i == 0:
                                            pkt_1 = pkt.encode()
                                        elif i == 1:
                                            paquetes = pkt.encode()
                                        else:
                                            paquetes += pkt.encode()
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
                                        + format(serv_id, "05d") # NOTE serv_id has 5 digits
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
                                    fog_sock[sock_index].sendall(pkt_1)
                                    sleep(delay/1000)
                                else:
                                    fog_sock[sock_index].sendall(pkt_1 + paquetes)
                                    sleep(delay/1000)
                        battery_prev = shared_data.battery
                        if s[0] == "local":
                            shared_data.battery = energy_consumption(
                                shared_data.battery, 0, delay, int(s[2])
                            )
                        elif s[0] == "fog":
                            shared_data.battery = energy_consumption(
                                shared_data.battery, 1, delay, int(s[2])
                            )
                        else:
                            shared_data.battery = energy_consumption(
                                shared_data.battery, 2, delay, int(s[2])
                            )

                        t_fin = datetime.now()
                        total_serv_len += int(s[2])

                    # Update reg by subtracting the packets already processed
                    reg[app_id][serv_id] = reg[app_id][serv_id] - total_serv_len
                    total_app_len += total_serv_len
            logger.debug("***** " + str(shared_data.serv_gen) + " *****")
            for a in reg:
                for s in reg[a]:
                    # Services with packets to be processed
                    if s != "detailed" and reg[a][s] != 0:
                        logger.debug("update rq -> " + str(s) + ": " + str(reg[a][s]))
                        rq[a].update({s: reg[a][s]})
                    else:
                        pass
                        logger.debug(
                            "no update rq -> " + str(s) + ": " + str(reg[a][s])
                        )
            logger.debug("Sumo 1 a serv_gen")
            # Counter of services generated by application. It matches the number of slots. It's used to build the serv_id.
            shared_data.serv_gen += 1
            f4.write(
                "iot"
                + str(shared_data.sys.argv[2])
                + ","
                + datetime.now().strftime("%H:%M:%S.%f")
                + ","
            )
            for buf in shared_data.q_app:
                if buf != shared_data.q_app[-1]:
                    f4.write(str(buf.qsize()) + ",")
            f4.write(str(buf.qsize()) + "\n")

            f6.write(
                "iot"
                + str(shared_data.sys.argv[2])
                + ","
                + str(shared_data.serv_gen)
                + ","
                + datetime.now().strftime("%H:%M:%S.%f")
                + ","
                + str(shared_data.battery)
                + "\n"
            )
  
        # To see packets that have not been processed
        for app_id in range(1, shared_data.num_app + 1):
            for serv_id in reg[app_id]:
                if serv_id != "detailed":
                    if reg[app_id][serv_id] != 0:
                        f5.write(str(serv_id) + "," + str(reg[app_id][serv_id]) + "\n")

    with open("res/serv_time_results"+str(id)+".txt", "w") as txt_file:
        json.dump(shared_data.serv_time_results, txt_file)
    if (
        shared_data.alg_name == "ActorCriticAgent"
        or shared_data.alg_name == "ActorCriticAgent_no_tf"
        or shared_data.alg_name == "DQN"
        or shared_data.alg_name == "q_learning"
        or shared_data.alg_name == "PPO"
    ):
        done = True
        if done and save_model:
            if shared_data.alg_name == "ActorCriticAgent" or shared_data.alg_name == "ActorCriticAgent_no_tf":
                parent_conn.send({"command": "save_model", "data": str(id)})
            elif shared_data.alg_name == "DQN":
                parent_conn.send({"command": "save_model", "data": str(id)})
            if shared_data.alg_name == "PPO":
                parent_conn.send({"command": "save_model", "data": str(id)})
            else:
                pass
                
        env.close()
        parent_conn.send({"command": "exit"})
        exit_status = parent_conn.recv()
        p.join()  
        
# Get information from the Cloud nodes and send it to the Master in the requests
# Now, this is only called once at the start of the simulation
def getCloudInfo(n):
    cloud_sock[n].send("InfoRq".encode())
    info = pickle.loads(cloud_sock[n].recv(1024))
    return info


def send_info_request(fog_control_sock, n, socket_lock):
    try:
        fog_control_sock.send("InfoRq".encode())
        logger.debug("Sending InfoRq")
    except Exception as e:
        logger.error(f"ERROR sending InfoRq: {e}")

# Receive feedback messages from the Fog node (and from the Cloud, forwarded by the Fog)
def handle_fog_messages(socket_lock):
    valid_headers = {
        b'\x01': 0, b'\x02': 1, b'\x03': 2, b'\x04': 3, b'\x05': 4,
        b'\x06': 5, b'\x07': 6, b'\x08': 7, b'\x09': 8, b'\x0A': 9,
        b'\x0B': 10, b'\x0C': 11, b'\x0D': 12, b'\x0E': 13, b'\x0F': 14,
        b'\x10': 15, b'\x11': 16, b'\x12': 17, b'\x13': 18, b'\x14': 19}
    while shared_data.end_event == False:
        try:
            logger.debug("Esperando mensaje del nodo Fog")
            data = fog_control_sock.recv(1024)
            logger.debug(f"***** Mensaje recibido del nodo Fog: {data}")
            delimiter = b'\xff'
            blocks = re.split(delimiter, data)
            blocks = [block for block in blocks if block] # Remove empty blocks
            if not data:
                logger.info("Connection closed by the Fog node")
                break
            logger.debug(f"Message received from the Fog node: {data}")
        except ConnectionResetError:
            logger.warning("Connection reset by the Fog node")
            break
        except OSError as e:
            logger.error(f"ERROR socket: {e}")
            break
        except Exception as e:
            logger.error(f"ERROR: {e}")
            break
        for d in blocks:
            logger.debug(f"Received {d}")
            header = d[:1]  # The first byte is the header
            logger.debug(f"Header: {header}, service {data}")
            try:
                if header in valid_headers:
                    decoded_data = d[1:].decode('utf-8')
                    serv, time = decoded_data.split(',')
                    # Feedback for the offloading algorithms
                    time_i = datetime.strptime(shared_data.services_gen[int(serv)], "%H:%M:%S.%f")
                    time_f = datetime.strptime(time, "%H:%M:%S.%f")
                    time_difference = (time_f - time_i).total_seconds() * 1000
                    shared_data.serv_time_results[int(serv)] = time_difference
                else:
                    fogInfo = pickle.loads(d)
                    logger.debug(f"Header no válido (es fogInfo): data = {fogInfo}")
                    shared_data.fogInfo = [fogInfo]
                    logger.debug(f'RECIBIDO FOGINFO CON Q = {fogInfo["proc1"]["q_len"]}')
            except Exception as e:
                logger.error(f"ERROR: {e} with {d}, obtained from {data}")

# Calculates the current buffer size. It is used for service generation
# Initially, all the packets in the buffer are assigned to a service in each slot
def calc_buf_size():
    buf_size = []
    for buf in shared_data.q_app:  # App buffers
        buf_size.append(buf.qsize())
    return buf_size

# Write processors state
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


# Wake up the traffic generators
def wakeup_trafficGen():
    for i in range(shared_data.num_app):
        shared_data.event_service[i].set()
        logger.debug("Wake up processor " + str(i))

# Calculate the reward using service time and battery consumption
def calc_reward(serv_id, dic_request, battery_prev, f7,d_req):
    logger.debug(f"EN CALC_REWARD()")
    try:
        logger.info(f"serv_id = {serv_id}")
        logger.info(f"d_req = {d_req}")
        if shared_data.serv_time_results[int(serv_id)] > int(d_req):
            logger.info(f'FAILURE: {str(serv_id)} shared_data.serv_time_results = {shared_data.serv_time_results[int(serv_id)]} > {d_req}')
            reward = PUNISHMENT
        elif shared_data.battery <= 0:
            logger.info(f'FAILURE: battery = {shared_data.battery}')
            reward = PUNISHMENT
        else:
            logger.info(f'SUCCESS: {str(serv_id)} shared_data.serv_time_results = {shared_data.serv_time_results[int(serv_id)]} < {d_req}')
            reward = (shared_data.battery - battery_prev)/100
            # reward = consumption
            logger.debug(f"shared_data.battery = {shared_data.battery}, battery_prev = {battery_prev}, reward = {reward}")
        f7.write(
            "iot"
            + str(shared_data.sys.argv[2])
            + ","
            + str(shared_data.serv_gen)
            + ","
            + datetime.now().strftime("%H:%M:%S.%f")
            + ","
            + str(reward)
            + "\n"
        )
        return reward
    except:
        logger.info(f"{serv_id} is not available in serv_time_results yet")
        reward = PUNISHMENT
        
        f7.write(
            "iot"
            + str(shared_data.sys.argv[2])
            + ","
            + str(shared_data.serv_gen)
            + ","
            + datetime.now().strftime("%H:%M:%S.%f")
            + ","
            + str(reward)
            + "\n"
        )
        return reward
    
def collect_info():
    iotInfo = {}
    iotInfo["battery"] = int(shared_data.battery)
    iotInfo["num_proc"] = shared_data.iot_num_proc
    iotInfo["buf_len"] = calc_buf_size()
    iotInfo["id"] = int(shared_data.sys.argv[2])
    # Crea un diccionario por cada procesador
    for i in range(1, shared_data.iot_num_proc + 1):
        iotInfo["proc" + str(i)] = {
            "q_len": shared_data.iot_dic_processor["q_1"].qsize(),
            "cola": shared_data.cola,
            "proc_cap": shared_data.iot_dic_processor["cap_" + str(i)],
            "processing": bool(shared_data.processing[i - 1]),
        }
    return iotInfo