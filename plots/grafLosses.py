from matplotlib import pyplot as plt
from collections import defaultdict
import matplotlib.pyplot as plt

def read_losses_from_file(filename="res/losses.txt"):
    # Dictionary to store losses for each unique device
    losses = defaultdict(lambda: {"actor": [], "critic": []})

    # Open the file and read the contents
    with open(filename, "r") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 4:
                device, service_id, actor_loss, critic_loss = parts
                losses[device]["actor"].append(float(actor_loss))
                losses[device]["critic"].append(float(critic_loss))

    return losses

def read_losses_from_file_DQN(filename="res/losses.txt"):
    losses = defaultdict(lambda: {"losses": []})
    
    with open(filename, "r") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 3:
                device, service_id, loss = parts
                losses[device]["losses"].append(float(loss))
    
    return losses

def plot_losses_DQN(filename):
    losses = read_losses_from_file_DQN(filename)
    
    for device, loss_data in losses.items():

        plt.plot(loss_data["losses"], label="Loss", color='blue')
        plt.xlabel("Update Steps")
        plt.ylabel("Loss")
        plt.grid(True)

        plt.tight_layout()
        plt.savefig(f"res/losses_{device}.png")
        plt.close()


def plot_losses_AC(filename):
    losses = read_losses_from_file(filename)

    for device, loss_data in losses.items():
        # Plot Actor Loss
        plt.subplot(1, 2, 1)
        plt.plot(loss_data["actor"], label="Actor Loss", color='blue')
        plt.xlabel("Update Steps")
        plt.ylabel("Loss")
        plt.title(f"Actor Loss Over Time ({device})")
        plt.legend()

        # Plot Critic Loss
        plt.subplot(1, 2, 2)
        plt.plot(loss_data["critic"], label="Critic Loss", color='orange')
        plt.xlabel("Update Steps")
        plt.ylabel("Loss")
        plt.title(f"Critic Loss Over Time ({device})")
        plt.legend()

        plt.tight_layout()
        plt.savefig(f"res/losses_{device}.png")  # Save with unique name
        plt.close()

# plot_losses_AC("res/losses.txt")
# plot_losses_DQN("res/losses.txt")