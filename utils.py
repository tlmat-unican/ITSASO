def energy_consumption(energy, action, tx_time, num_pkts):
    # TODO estos valores habría que obenerlos, les doy valores estandar
    p_tx = 1e-3
    processing_capacity = 1e8
    packet_size = 200
    required_cycles = 2e6
    k = 1e-23
    if action == 0 or action=="local":
        # Fuente: X. Lan, L. Cai and Q. Chen, "Execution Latency and Energy Consumption Tradeoff in Mobile-Edge Computing Systems," 2019 IEEE/CIC International Conference on Communications in China (ICCC), Changchun, China, 2019, pp. 123-128, doi: 10.1109/ICCChina.2019.8855969. keywords: {Mobile-edge computing;computation offloading;latency and energy tradeoff;distributed algorithm},
        consumption = k * num_pkts * processing_capacity * processing_capacity  * required_cycles * packet_size
        energy -= consumption
        # print(f"Local consumption: {consumption} | Local energy: {energy}", flush=True)
    else:
        consumption = float(p_tx) * float(tx_time) * num_pkts * packet_size
        energy -= consumption
        # print(
        #     f"Offload consumption: {consumption} | Offload energy: {energy} Eptx:{p_tx} | tx_time: {tx_time}",
        #     flush=True,
        # )

    if energy <= 0:
        return 0
    else:
        return energy
