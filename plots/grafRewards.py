import pandas as pd
from matplotlib import pyplot as plt
import glob
import json

with open("cnf/conf_DRL_params.json", "r") as jsonfile:
    config = json.load(jsonfile)
PUNISHMENT = config["punishment"]

def grafRewards(folder_path):
    device_data = {}
    files = glob.glob(folder_path + "/*Reward.txt")
    plt.clf()
    for file_path in files:
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split(',')  
                device = parts[0]  
                result = float(parts[3]) 

                if device not in device_data:
                    device_data[device] = []
                device_data[device].append(result)

    for device, results in device_data.items():
        x_values = range(len(results))
        plt.plot(x_values, results, marker='o', linestyle='-', label=device)
    plt.ylim(PUNISHMENT, 0.0)
    plt.xlabel('Service ID')
    plt.ylabel('Reward')
    plt.legend(title='iot #')
    plt.grid(True)
    plt.tight_layout()

    # Save the plot
    plt.savefig(folder_path + "/Rewards.png")
    plt.close()

def grafRewards_average(folder_path):
    device_data = {}
    files = glob.glob(folder_path + "/*Reward.txt")
    for file_path in files:
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split(',')  
                device = parts[0]  
                result = float(parts[3]) 

                if device not in device_data:
                    device_data[device] = []
                device_data[device].append(result)

    all_data = []
    for device, results in device_data.items():
        for service_id, reward in enumerate(results):
            all_data.append({'device': device, 'service_id': service_id, 'reward': reward})
    
    df = pd.DataFrame(all_data)

    mean_rewards = df.groupby('service_id')['reward'].mean()
    plt.clf()
    plt.plot(mean_rewards.index, mean_rewards.values, label='Mean Reward', color='blue', linewidth=2)
    plt.xlabel('Service ID')
    plt.ylabel('Reward')
    plt.ylim(PUNISHMENT, 0.0)
    plt.legend(title='Device')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(folder_path + "/Rewards_Mean.png")
    plt.close()

# grafRewards("res")
# grafRewards_average("res")