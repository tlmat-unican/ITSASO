import logging
import json
import time
from datetime import datetime
from utils import energy_consumption
import shared_data

logger = logging.getLogger('Basic DPP Algorithm')
logger.setLevel(logging.ERROR)

class Lyapunov:
    def __init__(self):
        self.G = 0
        self.serv_id = None
        self.delay_req = 0
        self._load_config()

    def _load_config(self):
        try:
            with open('cnf/config.json', 'r') as jsonfile:
                self.v = json.load(jsonfile)['simulation']['v']
        except Exception as e:
            logger.error(f"Error reading configuration: {e}")
            self.v = 0

    def _calculate_d(self, a, q, proc_cap, channel_delay_fog, channel_delay_cloud):
        return [
            (a + q[0]) / proc_cap[0],
            channel_delay_fog + (a + q[1]) / proc_cap[1],
            channel_delay_cloud + (a + q[2]) / proc_cap[2]
        ]

    def _solver(self):
        min_value, best_combination = float('inf'), None
        for i in range(3):
            combination = [1 if j == i else 0 for j in range(3)]
            value = (self.cost[i] * self.v) + (self.q[i] * (self.a - self.b[i])) + self.G * (self.d[i] - self.delay_req)
            if value < min_value:
                min_value, best_combination, self.delay_estimation = value, combination, self.d[i]
        return best_combination

    def _create_response(self, dic_serv, alfa):
        dic_rt = {i + 1: {} for i in range(self.num_app)}
        for m in range(self.num_app):
            for serv_id, p_serv in dic_serv[m + 1].items():
                if serv_id == 'detailed':
                    continue
                s = ''
                if alfa[self.num_proc]: s += f'fog::1::{p_serv}'
                elif alfa[self.num_proc + 1]: s += f'cloud::1::{p_serv}'
                else: s += f'local::1::{p_serv}'
                if s: dic_rt[m + 1][serv_id] = s
        return dic_rt

    def _update_G(self):
        serv_time = shared_data.serv_time_results.get(self.serv_id, 1000)
        self.G = max(self.G + (serv_time - self.delay_req), 0)

    def __call__(self, infoNode):
        start_time = time.time()
        if self.serv_id is not None:
            self._update_G()

        self.num_app, dic_serv = infoNode['service']['num_app'], infoNode['service']['dic_serv']
        fog_node = infoNode.get('fog', [])
        fog_node = fog_node[0] if fog_node and len(fog_node) > 0 else {}

        self.num_proc = fog_node.get('num_proc', 1)

        # Inicialization of variables (queues, processing capacities and delays)
        self.q = [
            infoNode['iot']['proc1']['q_len'],
            fog_node.get('proc1', {}).get('q_len', 0),
            0
        ]
        self.proc_cap = [
            infoNode['iot']['proc1']['proc_cap'] / 200 / 1000,
            fog_node.get('proc1', {}).get('proc_cap', float('inf')) / 200 / 1000,
            float('inf')
        ]

        self.delay_req = infoNode['service']['delay_req']
        self.channel_delay_fog = infoNode.get('delay_iot_fog', 0)
        self.channel_delay_cloud = self.channel_delay_fog + infoNode['delay_fog_cloud'][0]

        # Calculate parameters for the optimization problem
        self.a = next(iter(dic_serv[1].values()))
        self.b = [min(q_i, c_i) for q_i, c_i in zip(self.q, self.proc_cap)]
        self.d = self._calculate_d(self.a, self.q, self.proc_cap, self.channel_delay_fog, self.channel_delay_cloud)

        # Calculate the cost function (energy consumption)
        self.cost = [
            100 - energy_consumption(100, 0, 0, self.a),
            100 - energy_consumption(100, 1, self.channel_delay_fog, self.a),
            100 - energy_consumption(100, 2, self.channel_delay_cloud, self.a)
        ]

        # Solve the optimization problem
        res = self._solver()

        # Generate the response
        dic_rt = self._create_response(dic_serv, res)

        self.serv_id = list(dic_rt[1].keys())[0]
        return dic_rt