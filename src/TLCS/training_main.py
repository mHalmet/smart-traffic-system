from __future__ import absolute_import
from __future__ import print_function

import os
import datetime
from shutil import copyfile

from training_simulation import Simulation
from generator import TrafficGenerator
from memory import Memory
from model import TrainModel
from visualization import Visualization
from utils import import_train_configuration, set_sumo, set_train_path


if __name__ == "__main__":

    config = import_train_configuration(config_file='training_settings.ini')
    sumo_cmd = set_sumo(config['gui'], config['sumocfg_file_name'], config['max_steps'])
    path = set_train_path(config['models_path_name'])
    tl_names=["TLC",'TLN','TLE','TLS','TLW']

    model_dict={}
    memory_dict = {}
    for tl_name in tl_names:
        memory_dict[tl_name]= Memory(
            config['memory_size_max'],
            config['memory_size_min']
        )
        model_dict[tl_name]= TrainModel(
        config['num_layers'],
        config['width_layers'],
        config['batch_size'],
        config['learning_rate'],
        input_dim=config['num_states'],
        output_dim=config['num_actions']
    )

    trafficGen = TrafficGenerator(
        config['max_steps'], 
        config['n_cars_generated']
    )

    visualization = Visualization(
        path, 
        dpi=96
    )

    simulation= Simulation(
        model_dict,
        memory_dict,
        trafficGen,
        sumo_cmd,
        config['gamma'],
        config['max_steps'],
        config['green_duration'],
        config['yellow_duration'],
        config['num_states'],
        config['num_actions'],
        config['training_epochs'],
        tl_names, # trafficlight names
        # inbound edges
        {"TLC":['TLN2TLC','TLE2TLC','TLS2TLC','TLW2TLC'],"TLN":['N2TLN', 'E2TLN', 'TLC2TLN', 'W2TLN'] ,"TLE":['N2TLE', 'E2TLE', 'S2TLE', 'TLC2TLE'],"TLS":['TLC2TLS', 'E2TLS', 'S2TLS', 'W2TLS'],"TLW":['N2TLW', 'TLC2TLW', 'S2TLW', 'W2TLW']},
        # outbound edges
        {"TLC":['TLC2TLN', 'TLC2TLE', 'TLC2TLS', 'TLC2TLW'],"TLN":['TLN2N', 'TLN2E', 'TLN2TLC', 'TLN2TLW'],"TLE":['TLE2N','TLE2E','TLE2S','TLE2TLC'] ,"TLS:":['TLS2TLC', 'TLS2E', 'TLS2S', 'TLS2W'],"TLW":['TLW2N', 'TLW2TLC', 'TLW2S', 'TLW2W']}
    )

    episode = 0
    timestamp_start = datetime.datetime.now()
    
    while episode < config['total_episodes']:
        print('\n----- Episode', str(episode+1), 'of', str(config['total_episodes']))
        epsilon = 1.0 - (episode / config['total_episodes'])  # set the epsilon for this episode according to epsilon-greedy policy
        simulation_time, training_time = simulation.run(episode, epsilon)  # run the simulation
        print('Simulation time:', simulation_time, 's - Training time:', training_time, 's - Total:', round(simulation_time+training_time, 1), 's')
        episode += 1

    print("\n----- Start time:", timestamp_start)
    print("----- End time:", datetime.datetime.now())
    print("----- Session info saved at:", path)

    for tl_name in tl_names:
        full_path=path+"_"+tl_name
        model_dict[tl_name].save_model(full_path)

    copyfile(src='training_settings.ini', dst=os.path.join(path, 'training_settings.ini'))

    Visualization.save_data_and_plot(data=simulation.reward_store, filename='reward', xlabel='Episode', ylabel='Cumulative negative reward')
    Visualization.save_data_and_plot(data=simulation.cumulative_wait_store, filename='delay', xlabel='Episode', ylabel='Cumulative delay (s)')
    Visualization.save_data_and_plot(data=simulation.avg_queue_length_store, filename='queue', xlabel='Episode', ylabel='Average queue length (vehicles)')