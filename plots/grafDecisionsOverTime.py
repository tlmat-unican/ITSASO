import pandas as pd
from matplotlib import pyplot as plt
from collections import Counter
import glob
import numpy as np

def grafDecisionsOverTime(folder_path):
    color_mapping = {'local': 'blue', 'fog': 'green', 'cloud': 'orange'}
    id_data = {}
    devices=[]
    files = glob.glob(folder_path + "/*Assigment.txt")

    for file_path in files:
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                id_value = parts[0]  
                message = parts[2]  
                devices.append(parts[3])

                decision = message.split('::')[0].strip()

                if id_value not in id_data:
                    id_data[id_value] = Counter()

                id_data[id_value][decision] += 1

    id_df = pd.DataFrame(id_data).fillna(0).astype(int)
    id_df.index.name = 'Decision'
    id_df = id_df.T  # Transpose for easier plotting (ID on rows, Decisions as columns)

    ids = id_df.index
    bottom_values = [0] * len(ids)
    plt.clf()
    decision_order = ["local", "fog", "cloud"]
    id_df = id_df.reindex(columns=decision_order, fill_value=0)  # Ensure all columns exist
  
    for decision in decision_order:
        color = color_mapping.get(decision, plt.cm.tab10(hash(decision) % 10)) 
        plt.bar(
            ids, 
            id_df[decision], 
            bottom=bottom_values,  # Stack on top of the previous bars
            label=decision,            
            color=color
        )
        # Update the bottom values for stacking
        bottom_values = [bottom + value for bottom, value in zip(bottom_values, id_df[decision])]
    
    # Customization
    plt.yticks(np.arange(0, len(set(devices))+1, 1))
    plt.xlabel('Service ID')
    plt.ylabel('Count of Devices')
    step_size = max(1, len(ids) // 10)
    plt.xticks(ticks=range(0, len(ids), step_size), labels=ids[::step_size]) 
    plt.grid(True,)
    plt.legend(title='Decision', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.xlim(-1, len(ids))  # Extend the x-axis to fit all IDs
    plt.ylim(0, len(set(devices)))  # Set the y-axis limit

    # Save the plot
    plt.savefig(folder_path + "/DecisionsOverTime.png")
    plt.savefig(folder_path + "/DecisionsOverTime.svg")
    plt.close()

# grafDecisionsOverTime("./res")
