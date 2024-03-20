from mesa import Model
from mesa.time import BaseScheduler
from mesa.space import ContinuousSpace
from components import Source, Sink, SourceSink, Bridge, Link, Intersection, Vehicle
import pandas as pd
from collections import defaultdict
from statistics import mean
from mesa.datacollection import DataCollector
import networkx as nx
import matplotlib.pyplot as plt
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
# ---------------------------------------------------------------
def get_steps(model):
    return model.schedule.steps


def get_avg_delay(model):
    """
    Returns the average delay time
    """
    delays = [a.delay_time for a in model.schedule.agents if isinstance(a, Bridge)]
    return mean(delays)


def get_avg_driving(model):
    """
    Returns the average driving time of vehicles on road N1
    """

    if len(model.driving_time_of_trucks) > 0:
        return sum(model.driving_time_of_trucks) / len(model.driving_time_of_trucks)
    else:
        return 0


def get_conditions(model) -> object:
    """
    Returns the frequency of conditions for each step
    """
    conditions = [a.condition for a in model.schedule.agents if isinstance(a, Bridge)]
    freq_a = conditions.count('A')  # retrieve frequency of condition A in list of conditions per step
    freq_b = conditions.count('B')  # retrieve frequency of condition B in list of conditions per step
    freq_c = conditions.count('C')  # retrieve frequency of condition C in list of conditions per step
    freq_d = conditions.count('D')  # retrieve frequency of condition D in list of conditions per step
    freq_x = conditions.count('X')  # retrieve frequency of condition X in list of conditions per step
    return freq_a, freq_b, freq_c, freq_d, freq_x  # return frequencies


def get_condition_frequency_a(model):
    """
    Retrieve the frequency of condition A
    """
    return get_conditions(model)[0]


def get_condition_frequency_b(model):
    """
    Retrieve the frequency of condition B
    """
    return get_conditions(model)[1]


def get_condition_frequency_c(model):
    """
    Retrieve the frequency of condition C
    """
    return get_conditions(model)[2]


def get_condition_frequency_d(model):
    """
    Retrieve the frequency of condition D
    """
    return get_conditions(model)[3]


def get_condition_frequency_x(model):
    """
    Retrieve the frequency of condition X
    """
    return get_conditions(model)[4]

def set_lat_lon_bound(lat_min, lat_max, lon_min, lon_max, edge_ratio=0.02):
    """
    Set the HTML continuous space canvas bounding box (for visualization)
    give the min and max latitudes and Longitudes in Decimal Degrees (DD)

    Add white borders at edges (default 2%) of the bounding box
    """

    lat_edge = (lat_max - lat_min) * edge_ratio
    lon_edge = (lon_max - lon_min) * edge_ratio

    x_max = lon_max + lon_edge
    y_max = lat_min - lat_edge
    x_min = lon_min - lon_edge
    y_min = lat_max + lat_edge
    return y_min, y_max, x_min, x_max


# ---------------------------------------------------------------
class BangladeshModel(Model):
    """
    The main (top-level) simulation model

    One tick represents one minute; this can be changed
    but the distance calculation need to be adapted accordingly

    Class Attributes:
    -----------------
    step_time: int
        step_time = 1 # 1 step is 1 min

    path_ids_dict: defaultdict
        Key: (origin, destination)
        Value: the shortest path (Infra component IDs) from an origin to a destination

        Only straight paths in the Demo are added into the dict;
        when there is a more complex network layout, the paths need to be managed differently

    sources: list
        all sources in the network

    sinks: list
        all sinks in the network

    """

    step_time = 1

    file_name = '../data/demo-4.csv'

    def __init__(self, seed=None, x_max=500, y_max=500, x_min=0, y_min=0, collapse_dict:defaultdict={'A': 0, 'B': 0, 'C': 0, 'D': 0, 'X': 0}, routing_type: str = "random"):

        self.routing_type = routing_type
        self.collapse_dict = collapse_dict
        self.schedule = BaseScheduler(self)
        self.running = True
        self.path_ids_dict = defaultdict(lambda: pd.Series())
        self.shortest_path_dict = defaultdict(lambda: pd.Series())
        self.space = None
        self.sources = []
        self.sinks = []
        self.G= nx.DiGraph() #initialise network


        self.long_length_threshold = 200
        self.medium_length_threshold = 50
        self.short_length_threshold = 10
        self.generate_network()
        self.generate_model()

        self.driving_time_of_trucks = []

    def generate_network(self):
        """
        generate the network used within the simulation model
        returns a multi directed graph which includes bridges and intersections between roads
        """

        # import data
        df = pd.read_csv('../data/bridges_intersections_links.csv')
        # drop old id
        df = df.drop("id", axis='columns')
        # sort roads dataframe based on road name and chainage
        df = df.sort_values(by=['road', 'km'])
        # reset index
        df = df.reset_index(drop=False)
        # set new index as ID
        df.rename(columns={'index': 'id'}, inplace=True)
        # retrieve all roads in dataset
        roads = df['road'].unique().tolist()
        # initialize graph
        self.G = nx.DiGraph()
        # for each road in list roads
        for road in roads:
            # if equal to N1 or N2
            if road == 'N1' or road == 'N2':
                # subset all data points for the road
                road_subset = df[df['road'] == road]
                if road == 'N2':
                    # remove first row, which is intersection, if N2
                    road_subset = road_subset.iloc[1:, :]
                else:
                    # keep all data points if N1
                    road_subset = df[df['road'] == road]
                # get first row for N2, which is intersection with N1
                intersec_main = df[df.road == 'N2'].index[0]
                # now for each index, row in subset dataframe
                for index, row in road_subset.iterrows():
                    # if index does not equal intersection between N1 and N2, otherwise skip
                    if index != intersec_main:
                        self.G.add_node(row['id'], pos=(row['lat'], row['lon']), len=row['length'],
                                   typ=row['model_type'], intersec=row['intersec_to'])

                # retrieve all edges between bridges for one road
                edges = [(index, index + 1) for index, row in road_subset.iterrows()]
                # remove last one, which is out of bound
                edges.pop()
                # reverse subset
                road_subset_reversed = road_subset.iloc[::-1]
                # get all reversed indexes and add to list of edges
                edges += [(index, index - 1) for index, row in road_subset_reversed.iterrows()]
                # remove last one, which is out of bound
                edges.pop()
                # add all edges
                self.G.add_edges_from(edges)

                # get model type of all nodes
        typ = nx.get_node_attributes(self.G, 'typ')
        # get road which is intersected with N1 or N2
        intersec_to = nx.get_node_attributes(self.G, 'intersec')
        # get all key, value pairs in dictionaries
        for key_typ, value_typ in typ.items():
            # if value equals intersection as model type
            if value_typ == 'intersection':
                # get road name which intersects N1 or N2
                intersected_road = intersec_to[key_typ]
                # if road name not equal to N1 or N2
                if intersected_road != 'N1' and intersected_road != 'N2':
                    # subset data based on road name
                    road_subset = df[df['road'] == intersected_road]
                    # retrieve sourcesink of side road which became intersection
                    old_index = road_subset.iloc[0]['id']
                    # replace with intersection node on main road
                    df.loc[old_index, 'id'] = key_typ
                    # skip first row, which is old sourcesink of road
                    # now became intersection, already node of N1 or N2
                    road_subset = road_subset.iloc[1:, :]
                    # for each row in subset data
                    for index, row in road_subset.iterrows():
                        # add node based on index
                        self.G.add_node(row['id'], pos=(row['lat'], row['lon']), len=row['length'],
                                   typ=row['model_type'], intersec=row['intersec_to'])
                    # retrieve all edges between bridges for one road
                    edges = [(index, index + 1) for index, row in road_subset.iterrows()]
                    # remove last one, which is out of bound
                    edges.pop()
                    # reverse subset
                    road_subset_reversed = road_subset.iloc[::-1]
                    # get all reversed indexes and add to list of edges
                    edges += [(index, index - 1) for index, row in road_subset_reversed.iterrows()]
                    # remove last one, which is out of bound
                    edges.pop()
                    # add intersection edge between main and side road
                    intersected_edge = [(key_typ, road_subset.iloc[0]['id'])]
                    # to edges list
                    edges += intersected_edge
                    # also get reversed edge
                    rev_intersected_edge = [(road_subset.iloc[0]['id'], key_typ)]
                    # and add to edges list
                    edges += rev_intersected_edge
                    # add all edges
                    self.G.add_edges_from(edges)
                # if road equal to N1 or N2
                elif intersected_road == 'N1' or intersected_road == 'N2':
                    # subset data based on condition that road equals N2
                    road_subset = df[df['road'] == 'N2']
                    # retrieve first index, which is old sourcesink
                    old_index = road_subset.iloc[0]['id']
                    # replace old index with intersected node label with N1
                    df['id'].replace(old_index, key_typ)
                    # remove first row
                    road_subset = road_subset.iloc[1:, :]
                    # retrieve index
                    first_bridge_N2 = road_subset.iloc[0]['id']
                    # get intersected edge between N1 and N2
                    intersected_edge = [(key_typ, first_bridge_N2)]
                    # add intersected edge to list
                    edges += intersected_edge
                    # get reversed intersected edge
                    rev_intersected_edge = [(first_bridge_N2, key_typ)]
                    # also add reversed intersected edge
                    edges += rev_intersected_edge
                    # add edges to network
                    self.G.add_edges_from(edges)

        for u, v in self.G.edges:
            if abs(v - u) == 1:
                # obtain distance between nodes
                distance = abs((df.iloc[u, df.columns.get_indexer(['km'])].values) -
                               (df.iloc[v, df.columns.get_indexer(['km'])].values))
                # from kilometers to meters
                distance = distance * 1000
                # assign distance as weight to edge
                self.G[u][v]['weight'] = distance

            else:
                distance = abs((df.iloc[v - 1, df.columns.get_indexer(['km'])].values) -
                               (df.iloc[v, df.columns.get_indexer(['km'])].values))
                # from kilometers to meters
                distance = distance * 1000
                # assign distance as weight to edge
                self.G[u][v]['weight'] = distance

        # return network
        return self.G


    def generate_model(self):
        """
        generate the simulation model according to the csv file component information

        Warning: the labels are the same as the csv column labels

        """
        #TODO call generate_network method within generate_model method?
        #TODO alter generate model method accordingly
        df = pd.read_csv(self.file_name)

        # a list of names of roads to be generated
        roads = df['road'].unique().tolist()

        df_objects_all = []
        for road in roads:
            # Select all the objects on a particular road in the original order as in the cvs
            df_objects_on_road = df[df['road'] == road]

            if not df_objects_on_road.empty:
                df_objects_all.append(df_objects_on_road)

                """
                Set the path 
                1. get the serie of object IDs on a given road in the cvs in the original order
                2. add the (straight) path to the path_ids_dict
                3. put the path in reversed order and reindex
                4. add the path to the path_ids_dict so that the vehicles can drive backwards too
                """
                path_ids = df_objects_on_road['id']
                path_ids.reset_index(inplace=True, drop=True)
                self.path_ids_dict[path_ids[0], path_ids.iloc[-1]] = path_ids
                self.path_ids_dict[path_ids[0], None] = path_ids
                path_ids = path_ids[::-1]
                path_ids.reset_index(inplace=True, drop=True)
                self.path_ids_dict[path_ids[0], path_ids.iloc[-1]] = path_ids
                self.path_ids_dict[path_ids[0], None] = path_ids

        # put back to df with selected roads so that min and max and be easily calculated
        df = pd.concat(df_objects_all)
        y_min, y_max, x_min, x_max = set_lat_lon_bound(
            df['lat'].min(),
            df['lat'].max(),
            df['lon'].min(),
            df['lon'].max(),
            0.05
        )

        # ContinuousSpace from the Mesa package;
        # not to be confused with the SimpleContinuousModule visualization
        self.space = ContinuousSpace(x_max, y_max, True, x_min, y_min)

        for df in df_objects_all:
            for _, row in df.iterrows():  # index, row in ...

                # create agents according to model_type
                model_type = row['model_type'].strip()
                agent = None

                name = row['name']
                if pd.isna(name):
                    name = ""
                else:
                    name = name.strip()

                if model_type == 'source':
                    agent = Source(row['id'], self, row['length'], name, row['road'])
                    self.sources.append(agent.unique_id)
                elif model_type == 'sink':
                    agent = Sink(row['id'], self, row['length'], name, row['road'])
                    self.sinks.append(agent.unique_id)
                elif model_type == 'sourcesink':
                    agent = SourceSink(row['id'], self, row['length'], name, row['road'])
                    self.sources.append(agent.unique_id)
                    self.sinks.append(agent.unique_id)
                elif model_type == 'bridge':
                    agent = Bridge(row['id'], self, row['length'], name, row['road'], row['condition'])
                elif model_type == 'link':
                    agent = Link(row['id'], self, row['length'], name, row['road'])
                elif model_type == 'intersection':
                    if not row['id'] in self.schedule._agents:
                        agent = Intersection(row['id'], self, row['length'], name, row['road'])

                if agent:
                    self.schedule.add(agent)
                    y = row['lat']
                    x = row['lon']
                    self.space.place_agent(agent, (x, y))
                    agent.pos = (x, y)

    def get_random_route(self, source):
        """
        pick up a random route given an origin
        """
        while True:
            # different source and sink
            sink = self.random.choice(self.sinks)
            if sink is not source:
                break
        return self.path_ids_dict[source, sink]

    def get_shortest_path_route(self, source):
        """
        gives the shortest path between an origin and destination,
        based on bridge network defined using NetworkX library,
        and adds this path to path_ids_dict
        """
        # call network
        network = self.G
        #determine the sink to calculate the shortest path to
        while True:
            # different source and sink
            sink = self.random.choice(self.sinks)
            if sink is not source:
                break
        #the dictionary key is the origin, destination combination:
        key = source, sink
        # first, check if there already is a shortest path:
        if key in self.shortest_path_dict.keys():
            return self.shortest_path_dict[key]
        else:
            # compute shortest path between origin and destination based on distance (which is weight)
            shortest_path = nx.shortest_path(network, source, sink, weight='weight')
            # format shortest path in dictionary structure
            self.shortest_path_dict[key] = shortest_path
            return self.shortest_path_dict[key]

    def get_straight_route(self, source):
        """
        pick up a straight route given an origin
        """
        return self.path_ids_dict[source, None]

    def get_route(self, source):
        if self.routing_type == "random":
            return self.get_random_route(source)
        elif self.routing_type == "straight":
            return self.get_straight_route(source)
        elif self.routing_type == "shortest":
            return self.get_shortest_path_route(source)
        else:
            return self.get_straight_route(source)

    def step(self):
        """
        Advance the simulation by one step.
        """
        #self.datacollector.collect(self)
        self.schedule.step()

# EOF -----------------------------------------------------------
