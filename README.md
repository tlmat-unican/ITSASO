# ITSASO

<p align="center">
  <img src="Logo_ITSASO.png" />
</p>

## Description
ITSASO (IoT Task Simulation and Adaptive Scheduling for Offloading) is a simulator designed to optimize the management and scheduling of IoT tasks in a Fog-Cloud environment. It leverages adaptive scheduling algorithms to dynamically offload tasks based on the current environment conditions.

The development of this platform builds upon the work presented in [[1](#references)], extending and enhancing its capabilities for a more flexible and customizable Fog-Cloud computing environment. The latest version of the platform is detailed in [[2](#references)], which includes a comparison between Control Theory and DRL approaches for offloading scheduling.

## Features
- Simulation of IoT devices, Fog layer, and Cloud layer.
- Easy testing of offloading algorithms.
- High customization and flexibility for users.
- Lightweight containerization with Docker.

## Requirements
- Tested on: Ubuntu 20.04 LTS, Ubuntu 22.04 LTS  
- Python 3.8+
- Docker
- matplotlib\==3.5.3
- numpy<2.0.0
- pandas==2.2.2
- gymnasium==0.29.1
- psutil\==7.0.0

## Installation
1. Clone the repository:
   ```bash
   git clone git@github.com:necoville/ITSASO.git
   cd ITSASO
   ```
2. Install the required public libraries:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. Install Docker (see the [official documentation](https://docs.docker.com/engine/install/ubuntu/)).
## Usage
The configuration files are available in `conf/`.
   - **config.json:** Configuration file where users specify simulation settings.
   - **delay_requirements.csv:** Defines delay requirements for the IoT applications.
   - **tc_iot_fog_delay.csv:** Specifies transmission delays between IoT and Fog nodes.

The offloading algorithms must be in `alg/`. The platform includes by default some examples:
   - **All_local.py:** All services are processed at the local processor in the IoT node. 
   - **All_fog.py:** All services are processed at the Fog layer.
   - **All_cloud.py:** All services are processed at the Cloud layer.
   - **Random.py:** Randomly assigns services to IoT, Fog, or Cloud nodes.
   - **RR.py (Round Robin):** Distributes services cyclically among IoT, Fog, and Cloud nodes.
   - **Lyapunov.py:** Implements a stochastic optimization strategy based on Control Theory for dynamic task offloading. More details in [[2](#references)].

To run a simulation, use the script `simulate.py`:
   ```bash
   python3 simulate.py
   ```

For each simulation, many results files and the corresponding figures are generated in `res/`, including:  
- Battery evolution of IoT nodes 
- Decisions over time  
- Count of failed tasks per device  
- Number of failed tasks over time  
- Queue evolution for each node  
- Time elapsed in each Iot node's services

Further explanations can be found in [[2](#references)].

## License
This project is licensed under the GNU Affero General Public License v3.

## Contact
- Neco Villegas ([neco.villegas@unican.es](mailto:neco.villegas@unican.es))
- Gorka Nieto ([gnieto@ikerlan.es](mailto:gnieto@ikerlan.es))

## References
[1] N. Villegas, L. Diez, I. De La Iglesia, M. González-Hierro and R. Agüero, "Energy-Aware Optimum Offloading Strategies in Fog-Cloud Architectures: A Lyapunov Based Scheme," in IEEE Access, vol. 11, pp. 73116-73126, 2023, doi: 10.1109/ACCESS.2023.3295496.

[2] G. Nieto, N. Villegas, L. Diez, I. De La Iglesia, U. Lopez-Novoa, C. Perfecto and R. Agüero, "Comparing Control Theory and Deep Reinforcement Learning techniques for decentralized task offloading in the edge-cloud continuum," Elsevier SIMPAT, 2025. Manuscript under review.
