import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import itertools
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import re

def grafBat(node, num_iot, max_bat=100):
    all_data = []
    for i in range(1, num_iot + 1):
        file_path = f"./res/{node}Batt_{i}.txt"
        try:
            data_i = pd.read_csv(file_path, header=None, names=['node','serv_id', 'datetime', 'battery_level'])
            all_data.append(data_i)
        except FileNotFoundError:
            print(f"File not found: {file_path}", flush=True)
        plt.clf()
        plt.plot(data_i['serv_id'], data_i['battery_level'])
        plt.xlim(0, len(data_i['serv_id']))
        plt.ylim(0, max_bat)
        plt.xlabel('Time Slot')
        plt.ylabel('Battery Level')
        # plt.legend()
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.savefig(f"./res/{node}{i}_Battery.png")
        plt.close()

    data = pd.concat(all_data, ignore_index=True)
    battery_drain = []

    for device in data['node'].unique():
        device_data = data[data['node'] == device]
        plt.plot(
            device_data['serv_id'], 
            device_data['battery_level'], 
            label=device
        )
    # Compute battery drain for the device
        battery_drain.append(-np.diff(device_data['battery_level']))

    # Create a boxplot for battery drain across devices
    plt.figure()
    plt.boxplot(battery_drain, showmeans=True, patch_artist=True)
    plt.ylabel('Battery Drain per Time Slot')
    plt.xlabel('IoT Devices')
    plt.xticks(ticks=range(1, len(data['node'].unique()) + 1), labels=data['node'].unique(), rotation=45)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(f"./res/batteryBoxplot.png")
    plt.close()


def grafBat_average(node, num_iot, max_bat=100):
    plt.clf()
    all_data = []

    for i in range(1, num_iot + 1):
        file_path = f"./res/{node}Batt_{i}.txt"
        try:
            data_i = pd.read_csv(file_path, header=None, names=['node', 'serv_id', 'datetime', 'battery_level'])
            all_data.append(data_i)
        except FileNotFoundError:
            print(f"File not found: {file_path}", flush=True)

    combined_data = pd.concat(all_data, ignore_index=True)
    combined_data['serv_id'] = combined_data['serv_id'].astype(int)
    summary = combined_data.groupby('serv_id')['battery_level'].agg(['mean', 'std']).reset_index()

    service_ids = summary['serv_id']
    mean_battery = summary['mean']
    std_battery = summary['std']

    plt.plot(service_ids, mean_battery, label='Average Battery Level', color='blue', linewidth=2)
    plt.fill_between(
        service_ids,
        mean_battery - std_battery,
        mean_battery + std_battery,
        color='lightblue',
        alpha=0.5,
        label='Standard Deviation'
    )
    plt.xlim(0, len(service_ids))
    plt.ylim(0, max_bat)
    plt.xlabel('Service ID')
    plt.ylabel('Battery Level')
    plt.legend(loc='upper right')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(f"./res/average_Battery.png")
    plt.close()

    
def grafBat_every_alg(node, folder_list, num_iot, mapping_file,parent_folder="sim",j=0):
    plt.clf()
    colors = itertools.cycle([
        'blue', 'orange', 'green', 'red', 'purple', 'cyan', 
        'magenta', 'yellow', 'black', 'pink', 'brown', 'gray'
    ])
    linestyles = itertools.cycle(['-', '--', '-.', ':','solid', 'dashed', 'dashdot', 'dotted'])  # Different line styles

    legend_mapping = {}
    with open(mapping_file, "r") as file:
        for line in file:
            parts = line.strip().split("\t")
            if len(parts) == 3:
                folder_name, _, legend_label = parts
                legend_mapping[folder_name] = legend_label
            else:
                folder_name, _, legend_label,_ = parts
                legend_label="Lyapunov"
                legend_mapping[folder_name] = legend_label

    for folder_name in folder_list:
        all_data = []
        for i in range(1, num_iot + 1):
            file_path = f"./{parent_folder}/{folder_name}/{node}Batt_{i}.txt"
            try:
                data_i = pd.read_csv(file_path, header=None, names=['node', 'serv_id', 'datetime', 'battery_level'])
                all_data.append(data_i)
            except FileNotFoundError:
                print(f"File not found: {file_path}", flush=True)

        if not all_data:
            continue  # Skip if no data was loaded

        combined_data = pd.concat(all_data, ignore_index=True)
        combined_data['serv_id'] = combined_data['serv_id'].astype(int)
        summary = combined_data.groupby('serv_id')['battery_level'].agg(['mean', 'std']).reset_index()

        service_ids = summary['serv_id']
        mean_battery = summary['mean']
        std_battery = summary['std']

        # Assign color and linestyle
        color = next(colors)
        linestyle = next(linestyles)

        # Use the mapped legend label instead of the folder name
        legend_label = legend_mapping.get(folder_name, folder_name)

        plt.plot(service_ids, mean_battery, label=legend_label, color=color, linestyle=linestyle, linewidth=2)
        plt.fill_between(
            service_ids,
            mean_battery - std_battery,
            mean_battery + std_battery,
            color=color,
            alpha=0.2
        )

    plt.xlim(0, len(service_ids))
    plt.ylim(bottom=0)
    plt.xlabel('Service ID')
    plt.ylabel('Battery Level')
    
    plt.legend(loc='best')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    plt.savefig(f"./sim/average_Battery_{j}.png")
    plt.close()


def run_out_battery(node, num_iot,filepath):  
    results = []

    for i in range(1, num_iot + 1):
        file_path = f"{filepath}/{node}Batt_{i}.txt"
        try:
            data_i = pd.read_csv(file_path, header=None, names=['node', 'serv_id', 'datetime', 'battery_level'])
            depleted = data_i[data_i['battery_level'] == 0]
            if not depleted.empty:
                first_depletion = depleted.iloc[0]
                results.append((node, i, first_depletion['serv_id'], first_depletion['datetime']))

        except FileNotFoundError:
            print(f"File not found: {file_path}", flush=True)

    # Save results to file
    df_results = pd.DataFrame(results, columns=['node', 'file_index', 'serv_id', 'datetime'])
    df_results.to_csv(filepath+"/first_battery_depletion.csv", index=False)

    df_results = df_results.sort_values(by='file_index')
    plt.plot(df_results['file_index'], df_results['serv_id'], marker='o', linestyle='-', color='blue', label="First Depletion")

    min_val = df_results['serv_id'].min()
    max_val = df_results['serv_id'].max()
    mean_val = df_results['serv_id'].mean()
    
    with open(filepath + "/battery_ending_time.txt", "w") as file:
        file.write(f"Min: {min_val}\nMax: {max_val}\nMean: {mean_val:.2f}")
    # Add horizontal lines for min, max, and mean
    plt.axhline(y=min_val, color='green', linestyle='--', label=f"Min: {min_val}")
    plt.axhline(y=max_val, color='red', linestyle='--', label=f"Max: {max_val}")
    plt.axhline(y=mean_val, color='orange', linestyle='--', label=f"Mean: {mean_val:.2f}")

    # Labels and legend
    plt.xlabel('File Index')
    plt.ylabel('Service ID (First Depletion)')
    plt.title('Battery Depletion Moments per Node')
    plt.legend()
    plt.grid()
    plt.savefig("res/first_battery_depletion.png")

# run_out_battery("iot",15,filepath="./sim/sim1/")
# grafBat_every_alg("iot", ["sim1", "sim2", "sim3","sim4","sim5","sim6","sim7","sim8","sim9"], 15, "sim/info.txt",j=0)
