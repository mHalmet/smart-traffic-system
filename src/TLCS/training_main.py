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




    print("---------------------------------------------")
    print("Config loaded:")
    print(config['num_states'])
    print(config['model_type'])
    print(config['adjacent_tls'])
    print("---------------------------------------------")
    model_dict={}
    memory_dict = {}

    for tl_name in config['tl_names']:
        if (config['model_type'] == "disjoint"):
            num_states = config['num_states']
        elif (config['model_type'] == "collaborative-simple"):
            num_states = config['num_states'] + len((config['adjacent_tls'])[tl_name])
        elif (config['model_type'] == "collaborative-complex"):
            num_states = config['num_states'] * (len((config['adjacent_tls'])[tl_name])+1)
        elif (config['model_type'] == 'none'):
            num_states = 0


        memory_dict[tl_name]= Memory(
            config['memory_size_max'],
            config['memory_size_min']
        )

        print("NUM STATES IS:",num_states,";;;; WIDTH IS:",(int(num_states)*5))

        model_dict[tl_name] = TrainModel(
            config['num_layers'],
            input_dim=num_states,
            output_dim=config['num_actions'],
            #width of layers is statesize*5
            width=(int(num_states)*5),
            batch_size=config['batch_size'],
            learning_rate=config['learning_rate'],
        )

    trafficGen = TrafficGenerator(
        config['max_steps'], 
        config['n_cars_generated'],
        config['simulation_mode'],
        config['edge_dict'],
        config['start_points'],
        config['end_points']
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
        config['tl_names'],
        config['edges_in'],
        config['edges_out'],
        config['model_type'],
        config['adjacent_tls']
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

    for tl_name in config['tl_names']:
        full_path=path+"_"+tl_name
        model_dict[tl_name].save_model(full_path)

    copyfile(src='training_settings.ini', dst=os.path.join(path, 'training_settings.ini'))

    visualization.save_data_and_plot(data=simulation.reward_store, filename='reward', xlabel='Episode', ylabel='Cumulative negative reward',tl_names=config['tl_names'])
    visualization.save_data_and_plot(data=simulation.cumulative_wait_store, filename='delay', xlabel='Episode', ylabel='Cumulative delay (s)',tl_names=config['tl_names'])
    visualization.save_data_and_plot(data=simulation.avg_queue_length_store, filename='queue', xlabel='Episode', ylabel='Average queue length (vehicles)',tl_names=config['tl_names'])