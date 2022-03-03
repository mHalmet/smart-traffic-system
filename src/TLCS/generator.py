import numpy as np
import math

class TrafficGenerator:




    def __init__(self, max_steps, n_cars_generated,simulation_case):
        self._n_cars_generated = n_cars_generated  # how many cars per episode
        self._max_steps = max_steps
        self.simulation_case = simulation_case

    def generate_routefile(self, seed):
        if(self.simulation_case=="full"):
            self.generate_routes_full(seed)
        elif(self.simulation_case=="single"):
            self.genereate_routes_single(seed)
        elif(self.simulation_case=="double"):
            self.generate_routes_double(seed)
        elif (self.simulation_case == "tripple"):
            self.generate_routes_tripple(seed)


    def generate_routes(self,seed,edge_dict,starting_points):
        route_set = set()
        #create all possible routes recursively
        def buildRoute(currentRoute, currentKey):
            currentRoute = currentRoute + " " + currentKey
            if (currentKey in edge_dict):
                for k in edge_dict[currentKey]:
                    buildRoute(currentRoute, k)
            else:
                route_set.add(currentRoute.lstrip())

        for start in starting_points:
            buildRoute("", start)

        route_list = list(route_set)
        """
        Generation of the route of every car for one episode
        """
        np.random.seed(seed)  # make tests reproducible

        # the generation of cars is distributed according to a weibull distribution
        timings = np.random.weibull(2, 1000)
        timings = np.sort(timings)

        # reshape the distribution to fit the interval 0:max_steps
        car_gen_steps = []
        min_old = math.floor(timings[1])
        max_old = math.ceil(timings[-1])
        min_new = 0
        max_new = 100
        for value in timings:
            car_gen_steps = np.append(car_gen_steps,
                                      ((max_new - min_new) / (max_old - min_old)) * (value - max_old) + max_new)

        car_gen_steps = np.rint(
            car_gen_steps)  # round every value to int -> effective steps when a car will be generated

        # produce the file for cars generation, one car per line
        with open("intersection/episode_routes.rou.xml", "w") as routes:

            print("""<routes>
                            <vType accel="1.0" decel="4.5" id="standard_car" length="5.0" minGap="2.5" maxSpeed="25" sigma="0.5" />""",
                  file=routes)
            for r in route_set:
                print(f"<route id=\"{r}\" edges=\"{r}\"/>", file=routes)

            for car_counter, step in enumerate(car_gen_steps):
                r_id = np.random.randint(0, len(route_list))
                print(
                    '    <vehicle id="vehicle_%i" type="standard_car" route=%r depart="%s" departLane="random" departSpeed="10"/>' % (
                        car_counter, route_list[r_id], step), file=routes)
            print("</routes>", file=routes)

    def generate_routes_double(self, seed):
        edge_dict = {
            "N2TLW": ["TLW2S", "TLW2W", "TLW2TLE"],
            "S2TLW": ["TLW2N", "TLW2TLE", "TLW2W"],
            "W2TLW": ["TLW2N", "TLW2TLE", "TLW2S"],
            "TLE2TLW": ["TLW2N", "TLW2W", "TLW2S"],
            "TLW2TLE": ["TLE2N", "TLE2S", "TLE2E"],

            "N2TLE": ["TLE2E", "TLE2S", "TLE2TLW"],
            "E2TLE": ["TLE2N", "TLE2S", "TLE2TLW"],
            "S2TLE": ["TLE2N", "TLE2E", "TLE2TLW"]}
        # Use recursion to build all possible routes from possible starting points
        starting_points = ["N2TLW","W2TLW","S2TLW","N2TLE","E2TLE","S2TLE"]

        self.generate_routes(seed,edge_dict,starting_points)

    def generate_routes_tripple(self, seed):
        edge_dict = {
            "N2TLW": ["TLW2S", "TLW2W", "TLW2TLC"],
            "S2TLW": ["TLW2N", "TLW2TLC", "TLW2W"],
            "W2TLW": ["TLW2N", "TLW2TLC", "TLW2S"],
            "TLC2TLW": ["TLW2N", "TLW2W", "TLW2S"],

            "TLW2TLC": ["TLC2N", "TLC2TLE", "TLC2S"],
            "TLE2TLC": ["TLC2N", "TLC2TLW", "TLC2S"],
            "N2TLC": ["TLC2S", "TLC2TLW", "TLC2TLE"],
            "S2TLC": ["TLC2N", "TLC2TLE", "TLC2TLW"],

            "N2TLE": ["TLE2S", "TLE2E", "TLE2TLC"],
            "S2TLE": ["TLE2N", "TLE2TLC", "TLE2E"],
            "E2TLE": ["TLE2N", "TLE2TLC", "TLE2S"],
            "TLC2TLE": ["TLE2N", "TLE2E", "TLE2S"],
            }
        # Use recursion to build all possible routes from possible starting points
        starting_points = ["N2TLW","W2TLW","S2TLW","N2TLE","E2TLE","S2TLE","N2TLC","S2TLC"]

        self.generate_routes(seed, edge_dict, starting_points)




    def generate_routes_full(self, seed):
        edge_dict = {
            "N2TLN": ["TLN2E", "TLN2W", "TLN2TLC"],
            "E2TLN": ["TLN2N", "TLN2W", "TLN2TLC"],
            "TLC2TLN": ["TLN2N", "TLN2W", "TLN2E"],
            "W2TLN": ["TLN2N", "TLN2E", "TLN2TLC"],
            "TLN2TLC": ["TLC2TLE", "TLC2TLW", "TLC2TLS"],

            "E2TLE": ["TLE2N", "TLE2S", "TLE2TLC"],
            "N2TLE": ["TLE2E", "TLE2S", "TLE2TLC"],
            "TLC2TLE": ["TLE2N", "TLE2E", "TLE2S"],
            "S2TLE": ["TLE2N", "TLE2E", "TLE2TLC"],
            "TLE2TLC": ["TLC2TLN", "TLC2TLW", "TLC2TLS"],

            "W2TLW": ["TLW2N", "TLW2S", "TLW2TLC"],
            "N2TLW": ["TLW2S", "TLW2W", "TLW2TLC"],
            "TLC2TLW": ["TLW2N", "TLW2W", "TLW2S"],
            "S2TLW": ["TLW2N", "TLW2W", "TLW2TLC"],
            "TLW2TLC": ["TLC2TLN", "TLC2TLE", "TLC2TLS"],

            "S2TLS": ["TLS2E", "TLS2W", "TLS2TLC"],
            "E2TLS": ["TLS2S", "TLS2W", "TLS2TLC"],
            "TLC2TLS": ["TLS2S", "TLS2W", "TLS2E"],
            "W2TLS": ["TLS2S", "TLS2E", "TLS2TLC"],
            "TLS2TLC": ["TLC2TLN", "TLC2TLE", "TLC2TLW"]}
        # Use recursion to build all possible routes from possible starting points
        starting_points = ["N2TLN", "E2TLN", "W2TLN", "E2TLE", "N2TLE", "S2TLE", "W2TLW", "N2TLW", "S2TLW", "S2TLS",
                           "E2TLS", "W2TLS"]

        self.generate_routes(seed, edge_dict, starting_points)

    def genereate_routes_single(self, seed):
        """
        Generation of the route of every car for one episode
        """
        np.random.seed(seed)  # make tests reproducible

        # the generation of cars is distributed according to a weibull distribution
        timings = np.random.weibull(2, self._n_cars_generated)
        timings = np.sort(timings)

        # reshape the distribution to fit the interval 0:max_steps
        car_gen_steps = []
        min_old = math.floor(timings[1])
        max_old = math.ceil(timings[-1])
        min_new = 0
        max_new = self._max_steps
        for value in timings:
            car_gen_steps = np.append(car_gen_steps, ((max_new - min_new) / (max_old - min_old)) * (value - max_old) + max_new)

        car_gen_steps = np.rint(car_gen_steps)  # round every value to int -> effective steps when a car will be generated

        # produce the file for cars generation, one car per line
        with open("intersection/episode_routes.rou.xml", "w") as routes:
            print("""<routes>
            <vType accel="1.0" decel="4.5" id="standard_car" length="5.0" minGap="2.5" maxSpeed="25" sigma="0.5" />

            <route id="W_N" edges="W2TLC TLC2N"/>
            <route id="W_E" edges="W2TLC TLC2E"/>
            <route id="W_S" edges="W2TLC TLC2S"/>
            <route id="N_W" edges="N2TLC TLC2W"/>
            <route id="N_E" edges="N2TLC TLC2E"/>
            <route id="N_S" edges="N2TLC TLC2S"/>
            <route id="E_W" edges="E2TLC TLC2W"/>
            <route id="E_N" edges="E2TLC TLC2N"/>
            <route id="E_S" edges="E2TLC TLC2S"/>
            <route id="S_W" edges="S2TLC TLC2W"/>
            <route id="S_N" edges="S2TLC TLC2N"/>
            <route id="S_E" edges="S2TLC TLC2E"/>""", file=routes)

            for car_counter, step in enumerate(car_gen_steps):
                straight_or_turn = np.random.uniform()
                if straight_or_turn < 0.75:  # choose direction: straight or turn - 75% of times the car goes straight
                    route_straight = np.random.randint(1, 5)  # choose a random source & destination
                    if route_straight == 1:
                        print('    <vehicle id="W_E_%i" type="standard_car" route="W_E" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_straight == 2:
                        print('    <vehicle id="E_W_%i" type="standard_car" route="E_W" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_straight == 3:
                        print('    <vehicle id="N_S_%i" type="standard_car" route="N_S" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    else:
                        print('    <vehicle id="S_N_%i" type="standard_car" route="S_N" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                else:  # car that turn -25% of the time the car turns
                    route_turn = np.random.randint(1, 9)  # choose random source source & destination
                    if route_turn == 1:
                        print('    <vehicle id="W_N_%i" type="standard_car" route="W_N" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 2:
                        print('    <vehicle id="W_S_%i" type="standard_car" route="W_S" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 3:
                        print('    <vehicle id="N_W_%i" type="standard_car" route="N_W" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 4:
                        print('    <vehicle id="N_E_%i" type="standard_car" route="N_E" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 5:
                        print('    <vehicle id="E_N_%i" type="standard_car" route="E_N" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 6:
                        print('    <vehicle id="E_S_%i" type="standard_car" route="E_S" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 7:
                        print('    <vehicle id="S_W_%i" type="standard_car" route="S_W" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 8:
                        print('    <vehicle id="S_E_%i" type="standard_car" route="S_E" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)

            print("</routes>", file=routes)