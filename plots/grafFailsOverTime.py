import pandas as pd
from matplotlib import pyplot as plt
import glob
import numpy as np
import json

with open("cnf/conf_DRL_params.json", "r") as jsonfile:
    config = json.load(jsonfile)
PUNISHMENT = config["punishment"]

def grafFailsOverTime(folder_path):
    failure_data = {}
    timesteps = set()
    files = glob.glob(folder_path + "/*Reward.txt")
    devices=[]

    for file_path in files:
        with open(file_path, "r") as file:
            for line in file:
                parts = line.strip().split(",")
                timestep = parts[1]
                result = float(parts[3])
                devices.append(parts[0])

                timesteps.add(timestep)  # Track unique timesteps

                if timestep not in failure_data:
                    failure_data[timestep] = {"total": 0, "failed": 0}

                failure_data[timestep]["total"] += 1
                if result == PUNISHMENT:
                    failure_data[timestep]["failed"] += 1

    # Convert to DataFrame
    df = pd.DataFrame.from_dict(failure_data, orient="index").fillna(0).astype(int)
    df.index.name = 'timestep'
    
    plt.clf()
    ids=df.index
    plt.bar(ids, df["failed"], color='red', alpha=0.7,edgecolor="darkred",label='Failed Tasks')
    
    # Customization
    plt.yticks(np.arange(0, len(set(devices))+1, 1))
    plt.xlabel('Time')
    plt.ylabel('Number of Failed Tasks')
    step_size = max(1, len(ids) // 10)
    plt.xticks(ticks=range(0, len(ids), step_size), labels=ids[::step_size]) 
    plt.title('Failures Over Time')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend()
    plt.xlim(-1, len(ids))  # Extend the x-axis to fit all IDs
    plt.ylim(0, len(set(devices)))  # Set the y-axis limit

    # Save the plot
    plt.tight_layout()
    plt.savefig(folder_path + "/FailsOverTime.png")
    plt.close()

def FailsOverTimeWhileBattery(folder_path):
    df_rewards = pd.read_csv(folder_path + "/iotReward.txt", header=None, names=['device_id', 'time_id', 'timestamp', 'reward'])    
    merged_data = []

    files_battery = glob.glob(folder_path +"/iotBatt_*") 
    for battery_file in files_battery:
        df_bat = pd.read_csv(battery_file, header=None, names=['device_id', 'time_id', 'timestamp', 'battery'])
        df_merged = pd.merge(df_rewards, df_bat[['device_id', 'time_id', 'battery']], on=['device_id', 'time_id'], how='inner')
        merged_data.append(df_merged)

    df_final = pd.concat(merged_data, ignore_index=True)

    count = ((df_final['reward'] == -10) & (df_final['battery'] != 0)).sum()
    
    with open(folder_path + "/Fails_while_Battery.txt", "w") as file:
        file.write(f"Number of Fails while Battery: {count}")
    
    count_per_device = df_final[(df_final['reward'] == -10) & (df_final['battery'] != 0)].groupby('device_id').size().reset_index(name='count')

    count_per_device = count_per_device.sort_values(by="count", ascending=False)

    # Extract device IDs in sorted order
    devices = count_per_device["device_id"]

    # Get corresponding total tasks for sorted devices
    total_tasks_sorted = len(df_bat)

    # Plot total tasks (background bars)
    bars_total = plt.bar(
        devices, total_tasks_sorted, color="lightblue", alpha=0.4, edgecolor="black", label="Total Tasks"
    )

    # Plot filtered occurrences (foreground bars)
    bars_filtered = plt.bar(
        devices, count_per_device["count"], color="red", alpha=0.7, edgecolor="darkred", label="Fails with Battery"
    )

    # Annotate bars with numbers
    for bar in bars_filtered:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, height + 1, str(int(height)), ha='center', va='bottom', fontsize=10, color="black")

    plt.xlabel("Device ID")
    plt.ylabel("Number of Fails with Battery")
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.savefig(folder_path + "/Fails_while_Battery.png")
    plt.close()

# grafFailsOverTime("res")
# FailsOverTimeWhileBattery("res")
