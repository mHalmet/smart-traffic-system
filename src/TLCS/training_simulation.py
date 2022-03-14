import traci
import numpy as np
import random
import timeit
from multiprocessing.pool import ThreadPool as Pool
import traceback
import os
import tensorflow as tf

# phase codes based on environment.net.xml
PHASE_NS_GREEN = 0
PHASE_NS_YELLOW = 1
PHASE_NSL_GREEN = 2
PHASE_NSL_YELLOW = 3
PHASE_EW_GREEN = 4
PHASE_EW_YELLOW = 5
PHASE_EWL_GREEN = 6
PHASE_EWL_YELLOW = 7

pool_size=5

# define worker function before a Pool is instantiated


class Simulation:

    def __init__(self, model_dict, memory_dict, TrafficGen, sumo_cmd, gamma, max_steps, green_duration, yellow_duration, num_states, num_actions, training_epochs,tl_names,edges_in,edges_out,model_type,adjacent_tls):
        self._model_dict = model_dict
        self._memory_dict = memory_dict
        self._TrafficGen = TrafficGen
        self._gamma = gamma
        self._step = 0
        self._sumo_cmd = sumo_cmd
        self._max_steps = max_steps
        self._green_duration = green_duration
        self._yellow_duration = yellow_duration

        self._num_actions = num_actions

        self.tl_names = tl_names
        self.edges_in = edges_in
        self.edges_out = edges_out

        # model type effects what information is stored in the model state (whether actors share information or not)
        self.model_type = model_type
        #dictionary containing each adjacent tl to a given tl
        self.adjacent_tls=adjacent_tls

        #Initiate stores for each traffic light
        self._reward_store = {}
        self._cumulative_wait_store={}
        self._avg_queue_length_store={}
        self._num_states={}

        for tl_name in self.tl_names:
            if (self.model_type == "disjoint"):
                self._num_states[tl_name] = num_states
            elif (self.model_type == "collaborative-simple"):
                self._num_states[tl_name] = num_states + len(adjacent_tls[tl_name])
            elif (self.model_type  == "collaborative-complex"):
                self._num_states[tl_name] = num_states * (len(adjacent_tls[tl_name])+1)
            elif (self.model_type  =='none'):
                num_states = 0


            self.reward_store[tl_name]=[]
            self._cumulative_wait_store[tl_name]= []
            self._avg_queue_length_store[tl_name] = []
        self._training_epochs = training_epochs




    #worker function for parallelized training phase
    def worker(self,tl_name):
        try:
            self._replay(tl_name)
        except Exception as e:
            print('error with replay for',tl_name)
            print(traceback.print_exc())

    def run(self, episode, epsilon):
        """
        Runs an episode of simulation, then starts a training session
        """
        start_time = timeit.default_timer()

        # first, generate the route file for this simulation and set up sumo
        self._TrafficGen.generate_routefile(seed=episode)
        traci.start(self._sumo_cmd)
        print("Simulating...")

        # inits
        self._step = 0
        self._waiting_times = {}
        self._sum_neg_reward =  {}
        self._sum_queue_length =  {}
        self._sum_waiting_time =  {}
        old_total_wait =  {}
        old_state =  {}
        old_action =  {}
        next_action = {}
        yellowFlag = {}
        rewards = {}
        actions = {}
        current_states={}
        for tl_name in self.tl_names:
            self._waiting_times[tl_name]={}
            self._sum_neg_reward[tl_name]=0
            self._sum_queue_length[tl_name] = 0
            self._sum_waiting_time[tl_name] = 0
            old_total_wait[tl_name]=0
            old_state[tl_name]=-1
            old_action[tl_name]=-1
            actions[tl_name]=-1
            next_action[tl_name]=0
            rewards[tl_name]=0
            yellowFlag[tl_name]=False
        #get_state needs all actions to be initiated before being called
        for tl_name in self.tl_names:
            current_states[tl_name] = self._get_state(tl_name, actions)

        while self._step < self._max_steps:

            # calculate reward of previous action: (change in cumulative waiting time between actions)
            # waiting time = seconds waited by a car since the spawn in the environment, cumulated for every car in incoming lanes
            for tl_name in self.tl_names:

                if((next_action[tl_name]==0) & (yellowFlag[tl_name]==True)):
                    #print("TL",tl_name,"entering yellow phase action")
                    yellowFlag[tl_name]=False
                    self._set_green_phase(tl_name,actions[tl_name])
                    next_action[tl_name]= self._green_duration

                elif(next_action[tl_name]==0):

                    current_total_wait = self._collect_waiting_times(tl_name)

                    # get current state of the intersection
                    current_states[tl_name] = self._get_state(tl_name,old_action)

                    rewards[tl_name] = old_total_wait[tl_name] - current_total_wait

                    # saving only the meaningful reward to better see if the agent is behaving correctly
                    if rewards[tl_name] < 0:
                        self._sum_neg_reward[tl_name] += rewards[tl_name]

                    # saving the data into the memory
                    if self._step != 0:
                        self._memory_dict[tl_name].add_sample((old_state[tl_name], old_action[tl_name], rewards[tl_name], current_states[tl_name]))

                    # choose the light phase to activate, based on the current state of the intersection
                    actions[tl_name] = self._choose_action(tl_name,current_states[tl_name], epsilon)

                    if self._step != 0 and old_action[tl_name] != actions[tl_name]:
                        #Set traffic light to yellow
                        self._set_yellow_phase(tl_name,old_action[tl_name])
                        #wait for yellow period to end before executing action
                        next_action[tl_name] = self._yellow_duration
                        yellowFlag[tl_name] = True
                    else:
                        next_action[tl_name]= self._green_duration


                    # saving variables for later & accumulate reward
                    old_state[tl_name] = current_states[tl_name]
                    old_action[tl_name] = actions[tl_name]
                    old_total_wait[tl_name] = current_total_wait

                else:
                    #print("TL",tl_name," no step!")
                    next_action[tl_name]=next_action[tl_name]-1
            #Each iteration is one simulationstep
            self._simulate()

        self._save_episode_stats()
        for tl_name in self.tl_names:
            print("Total reward for",tl_name,":", self._sum_neg_reward[tl_name], "- Epsilon:", round(epsilon, 2))
        traci.close()
        simulation_time = round(timeit.default_timer() - start_time, 1)

        start_time = timeit.default_timer()
        pool = Pool(pool_size)
        for tl_name in self.tl_names:
            print("Training", tl_name, "...")

        print("Training traffic lights")
        for _ in range(self._training_epochs):
            #self._replay()
            pool.apply_async(self.worker, (tl_name,))
        pool.close()
        pool.join()
        training_time = round(timeit.default_timer() - start_time, 1)
        return simulation_time, training_time


    def _simulate(self):
        """
        Execute steps in sumo while gathering statistics
        """
        traci.simulationStep()  # simulate 1 step in sumo
        self._step += 1 # update the step counter
        #Add queue lengths for each step
        self._add_queue_lengths()
       # 1 step while wating in queue means 1 second waited, for each car, therefore queue_lenght == waited_seconds


    def _collect_waiting_times(self,tl_name):
        """
        Retrieve the waiting time of every car in the incoming roads
        """
        total_waiting_times={}
        car_list = traci.vehicle.getIDList()
        for car_id in car_list:
            #Accumulated waiting time contains waittime of previous intersection aswell! Either reset or keep as additional collaborative information
            wait_time = traci.vehicle.getAccumulatedWaitingTime(car_id)
            road_id = traci.vehicle.getRoadID(car_id)  # get the road id where the car is located

            if road_id in self.edges_in[tl_name]:  # consider only the waiting times of cars in incoming roads
                self._waiting_times[tl_name][car_id] = wait_time
            else:
                if car_id in self._waiting_times[tl_name]: # a car that was tracked has cleared the intersection
                    del self._waiting_times[tl_name][car_id]


        total_waiting_time = sum(self._waiting_times[tl_name].values())
        #total_waiting_times[tl_name]=total_waiting_time
        return total_waiting_time


    def _choose_action(self, tl_name,state, epsilon):
        """
        Decide wheter to perform an explorative or exploitative action, according to an epsilon-greedy policy
        """
        if random.random() < epsilon:
            return random.randint(0, self._num_actions - 1) # random action
        else:
            return np.argmax(self._model_dict[tl_name].predict_one(state)) # the best action given the current state


    def _set_yellow_phase(self, tl_name,old_action):
        """
        Activate the correct yellow light combination in sumo
        """
        yellow_phase_code = old_action * 2 + 1 # obtain the yellow phase code, based on the old action (ref on environment.net.xml)
        traci.trafficlight.setPhase(tl_name, yellow_phase_code)


    def _set_green_phase(self,tl_name, action_number):
        """
        Activate the correct green light combination in sumo
        """
        if action_number == 0:
            traci.trafficlight.setPhase(tl_name, PHASE_NS_GREEN)
        elif action_number == 1:
            traci.trafficlight.setPhase(tl_name, PHASE_NSL_GREEN)
        elif action_number == 2:
            traci.trafficlight.setPhase(tl_name, PHASE_EW_GREEN)
        elif action_number == 3:
            traci.trafficlight.setPhase(tl_name, PHASE_EWL_GREEN)


    def _add_queue_lengths(self):
        """
        Retrieve the number of cars with speed = 0 in every incoming lane
        """
        for tl_name in self.tl_names:
            halt_counts=[]
            for e in self.edges_in[tl_name]:
                halt_counts.append(traci.edge.getLastStepHaltingNumber(e))
            self._sum_queue_length[tl_name]=self._sum_queue_length[tl_name]+sum(halt_counts)
            self._sum_waiting_time[tl_name]=self._sum_waiting_time[tl_name]+sum(halt_counts)


    def disjoint_state(self,tl_name):
        state = np.zeros(self._num_states[tl_name])
        car_list = traci.vehicle.getIDList()

        for car_id in car_list:
            lane_pos = traci.vehicle.getLanePosition(car_id)
            lane_id = traci.vehicle.getLaneID(car_id)

            # split lane info into edge id and lane id (e.g. TLC2TLS_1 is the middle lane of TLC2TLS; '_2' is left turn only lane
            lane_info = lane_id.split("_")
            lane_pos = 650 - lane_pos  # inversion of lane pos, so if the car is close to the traffic light -> lane_pos = 0 --- 650 = max len of a road

            if (lane_info[0] in self.edges_in[tl_name]):

                # set lanegroup by using position of lane in the respective list
                lane_index = self.edges_in[tl_name].index(lane_info[0])

                # distance in meters from the traffic light -> mapping into cells
                if lane_pos < 7:
                    lane_cell = 0
                elif lane_pos < 14:
                    lane_cell = 1
                elif lane_pos < 21:
                    lane_cell = 2
                elif lane_pos < 28:
                    lane_cell = 3
                elif lane_pos < 40:
                    lane_cell = 4
                elif lane_pos < 60:
                    lane_cell = 5
                elif lane_pos < 100:
                    lane_cell = 6
                elif lane_pos < 160:
                    lane_cell = 7
                elif lane_pos <= 400:
                    lane_cell = 8
                elif lane_pos <= 650:
                    lane_cell = 9

                # finding the lane where the car is located
                # x2x_2 are the "turn left only" lanes
                if (lane_info[1] == '2'):
                    lane_group = lane_index * 2 + 1
                else:
                    lane_group = lane_index * 2

                if lane_group >= 1 and lane_group <= 7:
                    car_position = int(str(lane_group) + str(
                        lane_cell))  # composition of the two postion ID to create a number in interval 0-79
                    valid_car = True
                elif lane_group == 0:
                    car_position = lane_cell
                    valid_car = True
                else:
                    valid_car = False  # flag for not detecting cars crossing the intersection or driving away from it

                if valid_car:
                    state[
                        car_position] = 1  # write the position of the car car_id in the state array in the form of "cell occupied"

        return state

    def colab_simple_state(self,tl_name,actions):
        #Extend state by one value for each adjacent tls which will contain the next action
        state = np.zeros(self._num_states[tl_name])
        offset=len(self.adjacent_tls[tl_name])

        for ix,adjacent_tl in enumerate(self.adjacent_tls[tl_name]):
            state[ix]=actions[adjacent_tl]


        car_list = traci.vehicle.getIDList()

        for car_id in car_list:
            lane_pos = traci.vehicle.getLanePosition(car_id)
            lane_id = traci.vehicle.getLaneID(car_id)

            # split lane info into edge id and lane id (e.g. TLC2TLS_1 is the middle lane of TLC2TLS; '_2' is left turn only lane
            lane_info = lane_id.split("_")
            lane_pos = 650 - lane_pos  # inversion of lane pos, so if the car is close to the traffic light -> lane_pos = 0 --- 650 = max len of a road

            if (lane_info[0] in self.edges_in[tl_name]):

                # set lanegroup by using position of lane in the respective list
                lane_index = self.edges_in[tl_name].index(lane_info[0])

                # distance in meters from the traffic light -> mapping into cells
                if lane_pos < 7:
                    lane_cell = 0
                elif lane_pos < 14:
                    lane_cell = 1
                elif lane_pos < 21:
                    lane_cell = 2
                elif lane_pos < 28:
                    lane_cell = 3
                elif lane_pos < 40:
                    lane_cell = 4
                elif lane_pos < 60:
                    lane_cell = 5
                elif lane_pos < 100:
                    lane_cell = 6
                elif lane_pos < 160:
                    lane_cell = 7
                elif lane_pos <= 400:
                    lane_cell = 8
                elif lane_pos <= 650:
                    lane_cell = 9

                # finding the lane where the car is located
                # x2x_2 are the "turn left only" lanes
                if (lane_info[1] == '2'):
                    lane_group = lane_index * 2 + 1
                else:
                    lane_group = lane_index * 2

                if lane_group >= 1 and lane_group <= 7:
                    car_position = int(str(lane_group) + str(
                        lane_cell))  # composition of the two postion ID to create a number in interval 0-79
                    valid_car = True
                elif lane_group == 0:
                    car_position = lane_cell
                    valid_car = True
                else:
                    valid_car = False  # flag for not detecting cars crossing the intersection or driving away from it

                if valid_car:
                    state[offset+car_position] = 1  # write the position of the car car_id in the state array in the form of "cell occupied"

        return state


    def colab_complex_state(self,tl_name,actions):
        #Extend state by one value for each adjacent tls which will contain the next action
        state = np.zeros(self._num_states[tl_name])
        #offset=len(self.adjacent_tls[tl_name])
        tl_states=80



        car_list = traci.vehicle.getIDList()

        for car_id in car_list:
            lane_pos = traci.vehicle.getLanePosition(car_id)
            lane_id = traci.vehicle.getLaneID(car_id)

            # split lane info into edge id and lane id (e.g. TLC2TLS_1 is the middle lane of TLC2TLS; '_2' is left turn only lane
            lane_info = lane_id.split("_")
            lane_pos = 650 - lane_pos  # inversion of lane pos, so if the car is close to the traffic light -> lane_pos = 0 --- 650 = max len of a road

            if (lane_info[0] in self.edges_in[tl_name]):
                # set lanegroup by using position of lane in the respective list
                lane_index = self.edges_in[tl_name].index(lane_info[0])

                # distance in meters from the traffic light -> mapping into cells
                if lane_pos < 7:
                    lane_cell = 0
                elif lane_pos < 14:
                    lane_cell = 1
                elif lane_pos < 21:
                    lane_cell = 2
                elif lane_pos < 28:
                    lane_cell = 3
                elif lane_pos < 40:
                    lane_cell = 4
                elif lane_pos < 60:
                    lane_cell = 5
                elif lane_pos < 100:
                    lane_cell = 6
                elif lane_pos < 160:
                    lane_cell = 7
                elif lane_pos <= 400:
                    lane_cell = 8
                elif lane_pos <= 650:
                    lane_cell = 9

                # finding the lane where the car is located
                # x2x_2 are the "turn left only" lanes
                if (lane_info[1] == '2'):
                    lane_group = lane_index * 2 + 1
                else:
                    lane_group = lane_index * 2

                if lane_group >= 1 and lane_group <= 7:
                    car_position = int(str(lane_group) + str(
                        lane_cell))  # composition of the two postion ID to create a number in interval 0-79
                    valid_car = True
                elif lane_group == 0:
                    car_position = lane_cell
                    valid_car = True
                else:
                    valid_car = False  # flag for not detecting cars crossing the intersection or driving away from it

                if valid_car:
                    state[car_position] = 1  # write the position of the car car_id in the state array in the form of "cell occupied"

            else:
                #if not incomming edge of main TL check if adjacent tl
                for ix, adjacent_tl in enumerate(self.adjacent_tls[tl_name]):
                    if(lane_info[0] in self.edges_in[adjacent_tl]):
                        # set lanegroup by using position of lane in the respective list
                        lane_index = self.edges_in[adjacent_tl].index(lane_info[0])

                        # distance in meters from the traffic light -> mapping into cells
                        if lane_pos < 7:
                            lane_cell = 0
                        elif lane_pos < 14:
                            lane_cell = 1
                        elif lane_pos < 21:
                            lane_cell = 2
                        elif lane_pos < 28:
                            lane_cell = 3
                        elif lane_pos < 40:
                            lane_cell = 4
                        elif lane_pos < 60:
                            lane_cell = 5
                        elif lane_pos < 100:
                            lane_cell = 6
                        elif lane_pos < 160:
                            lane_cell = 7
                        elif lane_pos <= 400:
                            lane_cell = 8
                        elif lane_pos <= 650:
                            lane_cell = 9

                        # finding the lane where the car is located
                        # x2x_2 are the "turn left only" lanes
                        if (lane_info[1] == '2'):
                            lane_group = lane_index * 2 + 1
                        else:
                            lane_group = lane_index * 2

                        if lane_group >= 1 and lane_group <= 7:
                            car_position = int(str(lane_group) + str(
                                lane_cell))  # composition of the two postion ID to create a number in interval 0-79
                            valid_car = True
                        elif lane_group == 0:
                            car_position = lane_cell
                            valid_car = True
                        else:
                            valid_car = False  # flag for not detecting cars crossing the intersection or driving away from it

                        if valid_car:
                            # write the position of the car car_id in the state array in the form of "cell occupied"
                            # offset by adjacent traffic light (80 states for each TL)
                            state[car_position+((ix+1)*tl_states)] = 1






        return state

    def _get_state(self,tl_name,actions):
        """
        Retrieve the state of the intersection from sumo, in the form of cell occupancy
        """
        if(self.model_type=="disjoint"):
            return self.disjoint_state(tl_name)
        elif(self.model_type=="collaborative-simple"):
            return self.colab_simple_state(tl_name,actions)
        elif (self.model_type == "collaborative-complex"):
            return self.colab_complex_state(tl_name,actions)


    def _replay(self,tl_name):
        """
        Retrieve a group of samples from the memory and for each of them update the learning equation, then train
        """
        #for tl_name in self.tl_names:
        batch = self._memory_dict[tl_name].get_samples(self._model_dict[tl_name].batch_size)

        if len(batch) > 0:  # if the memory is full enough
            states = np.array([val[0] for val in batch])  # extract states from the batch
            next_states = np.array([val[3] for val in batch])  # extract next states from the batch

            # prediction
            q_s_a = self._model_dict[tl_name].predict_batch(states)  # predict Q(state), for every sample
            q_s_a_d = self._model_dict[tl_name].predict_batch(next_states)  # predict Q(next_state), for every sample

            # setup training arrays
            x = np.zeros((len(batch), self._num_states[tl_name]))
            y = np.zeros((len(batch), self._num_actions))

            for i, b in enumerate(batch):
                state, action, reward, _ = b[0], b[1], b[2], b[3]  # extract data from one sample
                current_q = q_s_a[i]  # get the Q(state) predicted before
                current_q[action] = reward + self._gamma * np.amax(q_s_a_d[i])  # update Q(state, action)
                x[i] = state
                y[i] = current_q  # Q(state) that includes the updated action value

            self._model_dict[tl_name].train_batch(x, y)  # train the NN


    def _save_episode_stats(self):
        """
        Save the stats of the episode to plot the graphs at the end of the session
        """
        for tl_name in self.tl_names:
            self._reward_store[tl_name].append(self._sum_neg_reward[tl_name])  # how much negative reward in this episode
            self._cumulative_wait_store[tl_name].append(self._sum_waiting_time[tl_name])  # total number of seconds waited by cars in this episode
            self._avg_queue_length_store[tl_name].append(self._sum_queue_length[tl_name] / self._max_steps)  # average number of queued cars per step, in this episode



    @property
    def reward_store(self):
        return self._reward_store


    @property
    def cumulative_wait_store(self):
        return self._cumulative_wait_store


    @property
    def avg_queue_length_store(self):
        return self._avg_queue_length_store

