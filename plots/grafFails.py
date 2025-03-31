from matplotlib import pyplot as plt
import glob
import json

with open("cnf/conf_DRL_params.json", "r") as jsonfile:
    config = json.load(jsonfile)
PUNISHMENT = config["punishment"]

def grafFails(folder_path):
    failure_data = {}
    files = glob.glob(folder_path + "/*Reward.txt")

    for file_path in files:
        with open(file_path, "r") as file:
            for line in file:
                parts = line.strip().split(",")
                device = parts[0]
                result = float(parts[3])

                if device not in failure_data:
                    failure_data[device] = {"total": 0, "failed": 0}

                failure_data[device]["total"] += 1
                if result == PUNISHMENT:
                    failure_data[device]["failed"] += 1

    devices = []
    total_tasks = []
    failed_tasks = []
    for device, counts in failure_data.items():
        devices.append(device.split("iot")[1])
        total_tasks.append(counts["total"])
        failed_tasks.append(counts["failed"])
    
    sorted_data = sorted(zip(devices, total_tasks, failed_tasks), key=lambda x: int(x[0]))
    devices, total_tasks, failed_tasks = zip(*sorted_data)  
    plt.clf()
    bars = plt.bar(
        devices,
        total_tasks,
        color="lightblue",
        alpha=0.4,
        edgecolor="black",
        label="Total Tasks",
    )

    for device, bar, total, failed in zip(devices, bars, total_tasks, failed_tasks):
        failed_height = (failed / total) * bar.get_height()
        plt.bar(
            device,
            failed_height,
            color="red",
            alpha=0.7,
            edgecolor="darkred",
            label=(
                "Failed Tasks"
                if "Failed Tasks" not in plt.gca().get_legend_handles_labels()[1]
                else ""
            ),
        )

        # Annotate each bar with failure quantity and percentage
        failure_percentage = (failed / total) * 100
        plt.text(
            bar.get_x() + bar.get_width() / 2,  # Center horizontally
            failed_height / 2,  # Center vertically within the red "fails" segment
            f"{failed}\n({failure_percentage:.1f}%)",
            ha="center",
            va="center",
            color="white",  # Use white for better contrast inside the red segment
            fontsize=10,
            fontweight="bold",
        )

    # Customization
    plt.xlabel("IoT Device")
    plt.ylabel("Services")
    plt.ylim(0, max(total_tasks))  # Extend y-axis for annotations
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.legend()
    plt.tight_layout()

    # Save the plot
    plt.savefig(folder_path + "/FailedTasksTotals.png")
    plt.close()


# grafFails("res")
