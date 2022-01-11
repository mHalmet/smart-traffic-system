import numpy as np
import math

class TrafficGenerator:




    def __init__(self, max_steps, n_cars_generated):
        self._n_cars_generated = n_cars_generated  # how many cars per episode
        self._max_steps = max_steps

    def generate_routefile(self, seed):
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
        route_set = set()

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
        with open("episode_routes.rou.xml", "w") as routes:

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

