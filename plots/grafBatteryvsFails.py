import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

def plot_battery_fails_scatter(folders, mapping_file, i=0, parent_folder="sim"):
    folder_labels = []
    fail_counts = []
    mean_values = []
    
    legend_mapping = {}
    with open(mapping_file, "r") as file:
        for line in file:
            parts = line.strip().split("\t")
            if len(parts) == 3:
                folder_name, _, legend_label = parts
            else:
                folder_name, _, legend_label, _ = parts
                legend_label = "Lyapunov"
            legend_mapping[folder_name] = legend_label

    colors = ["red", "green", "blue", "orange", "purple", "brown", "pink", "gray", "cyan", "magenta"]
    markers = ["o","v","^","<",">","s","P","+","x","D"]
    
    for folder in folders:
        folder_labels.append(folder)
        fails_path = os.path.join(parent_folder, folder, "Fails_while_Battery.txt")
        with open(fails_path, "r") as file:
            count = int(file.readline().strip().split(":")[-1].strip())  
            fail_counts.append(count)

        battery_path = os.path.join(parent_folder, folder, "battery_ending_time.txt")
        with open(battery_path, "r") as file:
            mean_val = file.readlines()[2].split(":")[-1].strip()  
            if mean_val is None or mean_val == "nan":
                mean_val = 1030 
            else:
                mean_val = float(mean_val)
            mean_values.append(mean_val)
        
    fig, ax = plt.subplots(figsize=(8, 6))

    for folder, x, y in zip(folders, mean_values, fail_counts):
        color = colors[folders.index(folder) % len(colors)]  
        marker = markers[folders.index(folder) % len(markers)]  
        ax.scatter(x, y, color=color, edgecolors="black", marker=marker,s=100, label=legend_mapping[folder])

    ax.set_xlim(-1, 1050)
    ax.set_ylim(max([y for x, y in zip(mean_values, fail_counts)])-max([y for x, y in zip(mean_values, fail_counts)])*1.05, max([y for x, y in zip(mean_values, fail_counts)])*1.05)
    ax.axvline(x=1000, color="black", linestyle="dashed", alpha=0.5)  # Indicate missing battery data

    ax.set_xlabel("Battery Ending Time")
    ax.set_ylabel("Fails Count")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)

    ### ZOOM IN
    ax_inset = inset_axes(ax, width="25%", height="25%",loc="lower left") 
    valid_x = [x for x in mean_values if 0 <= x <= 999]
    valid_y = [y for x, y in zip(mean_values, fail_counts) if 0 <= x <= 999]

    zoom_min_x, zoom_max_x = min(valid_x) * 0.9, max(valid_x) * 1.1
    zoom_min_y, zoom_max_y = max([y for x, y in zip(mean_values, fail_counts)])-max([y for x, y in zip(mean_values, fail_counts)])*1.01, max(valid_y) * 1.1

    for folder, x, y in zip(folders, mean_values, fail_counts):
        if 0 <= x <= 999:
            color = colors[folders.index(folder) % len(colors)]
            marker = markers[folders.index(folder) % len(markers)]  
            ax_inset.scatter(x, y, color=color, edgecolors="black", marker=marker,s=50, label=legend_mapping[folder])

    ax_inset.set_xlim(zoom_min_x, zoom_max_x)
    ax_inset.set_ylim(zoom_min_y, zoom_max_y)
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])

    plt.savefig(f"{parent_folder}/battery_vs_fails_scatter_{i}.png")
    
# plot_battery_fails_scatter(["sim1", "sim2", "sim3","sim4","sim5","sim6","sim7","sim8","sim9","sim10"],mapping_file="sim/info.txt",i=0,parent_folder="sim")
# plot_battery_fails_scatter(["sim11", "sim12", "sim13","sim14","sim15","sim16","sim17","sim18","sim19","sim20"],mapping_file="sim/info.txt",i=1,parent_folder="sim")