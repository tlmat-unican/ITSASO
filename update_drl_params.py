import json
import random
import shutil

def update_drl_params(config_path="cnf/conf_DRL_params.json", iterations=12):
    """
    Updates the discount factor, learning rates, and actor-critic network parameters
    in the specified JSON configuration file for multiple iterations.
    """
    # Load existing config
    with open(config_path, "r") as file:
        config = json.load(file)
    
    lr_values = [1e-5, 1e-4, 1e-3, 5e-5, 5e-4, 5e-3,
                 1e-5, 1e-4, 1e-3, 5e-5, 5e-4, 5e-3]  # Expanded learning rates
    
    for i in range(iterations):
        # Generate new values
        disc_fact = 0.95
        lr = random.choice(lr_values)  # Same learning rate for both actor and critic
        
        new_values = {
            "disc_fact": disc_fact,
            "lr_a": lr,
            "lr_c": lr,
        }
        
        # Update the main parameters
        config.update(new_values)
        
        # Update the nested actor_critic parameters with the same values
        if "actor_critic" in config:
            config["actor_critic"].update(new_values)
        
        # Save updated config for each iteration
        save_path = f"cnf/conf_DRL_params_iter_{i+1}.json"
        with open(save_path, "w") as file:
            json.dump(config, file, indent=4)
        
        print(f"Iteration {i+1}: Updated parameters saved to {save_path}")
    
    return f"Generated {iterations} different parameter sets."

def apply_iteration_config(iteration, config_dir="cnf"):
    """
    Replaces conf_DRL_params.json with a selected iteration file.
    """
    source_file = f"{config_dir}/conf_DRL_params_iter_{iteration}.json"
    target_file = f"{config_dir}/conf_DRL_params.json"
    
    try:
        shutil.copy(source_file, target_file)
        print(f"Applied configuration from {source_file} to {target_file}")
    except FileNotFoundError:
        print(f"Error: {source_file} not found.")
    
update_drl_params()