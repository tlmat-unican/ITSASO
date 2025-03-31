import csv
import matplotlib.pyplot as plt
import random

def generate_csv(num_iot, steps, min_value,max_value,filename):
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        for _ in range(num_iot):
            row = [random.randint(min_value, max_value) for _ in range(steps)]
            writer.writerow(row)

def plot_csv(filename):
    data = []
    
    # Read the CSV file
    with open(filename, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            data.append([int(value) for value in row])
    
    # Plot the data
    for i, row in enumerate(data):
        plt.plot(row, label=f'IoT Device {i+1}')
    
    plt.xlabel('Steps')
    plt.ylabel('Values')
    plt.title('IoT Data Plot')
    plt.legend()
    plt.savefig('cnf/delay_requirements.png')

generate_csv(20, 3000,250,1000, 'cnf/delay_requirements.csv')
# plot_csv('cnf/delay_requirements.csv')

#generate_csv(num_iot=20, steps=1000,min_value=50,max_value=125, filename='cnf/tc_iot_fog_delay.csv')