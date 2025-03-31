import pandas as pd
from matplotlib import pyplot as plt
from collections import Counter

def grafDec(node_name):
    file_path = "./res/" + node_name + "Assigment.txt" 
    word_counts = Counter()

    with open(file_path, 'r') as file:
        for line in file:
            entry = line.split(',')[2]
            word = entry.split('::')[0].strip()  
            word_counts[word] += 1

    categories = ['local', 'fog', 'cloud']
    data = [word_counts.get(category, 0) for category in categories]
        
    df = pd.DataFrame({'Word': categories, 'Count': data})
    total_count = df['Count'].sum()
    df['Percentage'] = (df['Count'] / total_count) * 100

    plt.clf()
    color_mapping = {'local': 'blue', 'fog': 'green', 'cloud': 'orange'}
    bars = plt.bar(df['Word'], df['Count'], color=[color_mapping[word] for word in df['Word']])
    plt.xlabel('Decisions')
    plt.ylabel('Count')
    for bar, percentage in zip(bars, df['Percentage']):
        plt.text(
            bar.get_x() + bar.get_width() / 2,  # Center of the bar
            bar.get_height() / 2,  # Midpoint of the bar
            f'{percentage:.1f}%',  # Format percentage with 1 decimal place
            ha='center',  # Center-align text
            va='center',  # Vertically align to center
            fontsize=9, color='white'  # Use white text for visibility
        )
    plt.tight_layout()
    plt.savefig("./res/" + node_name + "Decisions.png")
    plt.close()

    print(df['Percentage'])
    # print(df['Word'])

#grafDec("iot")