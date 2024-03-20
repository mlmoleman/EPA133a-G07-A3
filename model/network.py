# import libraries
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

def bridge_network():
    """
    returns a directed graph which includes bridges and intersections between roads
    """
    # import data
    df = pd.read_csv('../data/bridges_cleaned_intersected_long.csv')
    # remove unnecessary columns
    df.drop(columns=['Unnamed: 0'], inplace = True)
    # sort roads dataframe based on road name and chainage
    df = df.sort_values(by=['road', 'km'])
    # reset index
    df = df.reset_index(drop=False)
    # retrieve all roads in dataset
    roads = df['road'].unique().tolist()
    # initialize graph
    G= nx.DiGraph()
    # for each road in list roads
    for road in roads: 
        # if equal to N1 or N2
        if road == 'N1' or road == 'N2': 
            # subset all data points for the road
            road_subset = df[df['road'] == road]
            if road == 'N2': 
                # remove first row, which is intersection, if N2
                road_subset = road_subset.iloc[1:,:]
            else: 
                # keep all data points if N1
                road_subset = df[df['road'] == road]
            # get first row for N2, which is intersection with N1
            intersec_main = df[df.road == 'N2'].index[0]
            # now for each index, row in subset dataframe
            for index, row in road_subset.iterrows():
                # if index does not equal intersection between N1 and N2, otherwise skip
                if index != intersec_main: 
                    G.add_node(row['index'], pos = (row['lat'], row['lon']), len = row['length'], 
                               typ = row['model_type'], intersec = row['intersec_to'])
            # retrieve all edges between bridges for one road
            edges = [(index, index+1) for index, row in road_subset.iterrows()]
            # remove last one, which is out of bound
            edges.pop()
            # reverse subset
            road_subset_reversed = road_subset.iloc[::-1]
            # get all reversed indexes and add to list of edges
            edges += [(index, index-1) for index, row in road_subset_reversed.iterrows()]
            # remove last one, which is out of bound
            edges.pop()
            # add all edges 
            G.add_edges_from(edges)  
            
    # get model type of all nodes
    typ = nx.get_node_attributes(G, 'typ')
    # get road which is intersected with N1 or N2
    intersec_to = nx.get_node_attributes(G, 'intersec')
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
                old_index = road_subset.iloc[0]['index']
                # replace with intersection node on main road
                df.loc[old_index,'index'] = key_typ
                # skip first row, which is old sourcesink of road 
                # now became intersection, already node of N1 or N2
                road_subset = road_subset.iloc[1:,:]
                # for each row in subset data
                for index, row in road_subset.iterrows():
                    # add node based on index
                    G.add_node(row['index'], pos = (row['lat'], row['lon']), len = row['length'], 
                               typ = row['model_type'], intersec = row['intersec_to'])
                # retrieve all edges between bridges for one road
                edges = [(index, index+1) for index, row in road_subset.iterrows()]  
                # remove last one, which is out of bound
                edges.pop()
                # reverse subset
                road_subset_reversed = road_subset.iloc[::-1]
                # get all reversed indexes and add to list of edges
                edges += [(index, index-1) for index, row in road_subset_reversed.iterrows()]
                # remove last one, which is out of bound
                edges.pop()
                # add intersection edge between main and side road
                intersected_edge = [(key_typ, road_subset.iloc[0]['index'])]
                # to edges list
                edges += intersected_edge
                # also get reversed edge
                rev_intersected_edge = [(road_subset.iloc[0]['index'], key_typ)]
                # and add to edges list
                edges += rev_intersected_edge
                # add all edges  
                G.add_edges_from(edges)
            # if road equal to N1 or N2
            elif intersected_road == 'N1' or intersected_road == 'N2': 
                # subset data based on condition that road equals N2
                road_subset = df[df['road'] == 'N2']
                # retrieve first index, which is old sourcesink
                old_index = road_subset.iloc[0]['index']
                # replace old index with intersected node label with N1
                df['index'].replace(old_index, key_typ)
                # remove first row
                road_subset = road_subset.iloc[1:,:]
                # retrieve index
                first_bridge_N2 = road_subset.iloc[0]['index']
                # get intersected edge between N1 and N2
                intersected_edge = [(key_typ, first_bridge_N2)]
                # add intersected edge to list
                edges += intersected_edge
                # get reversed intersected edge
                rev_intersected_edge = [(first_bridge_N2, key_typ)]
                # also add reversed intersected edge
                edges += rev_intersected_edge
                # add edges to network
                G.add_edges_from(edges)
         
    for u,v in G.edges: 
        if abs(v - u) == 1: 
            # obtain distance between nodes
            distance = abs((df.iloc[u, df.columns.get_indexer(['km'])].values) - 
                           (df.iloc[v, df.columns.get_indexer(['km'])].values))
            # from kilometers to meters
            distance = distance * 1000 
            # assign distance as weight to edge
            G[u][v]['weight'] = distance
    
        else: 
            distance = abs((df.iloc[v-1, df.columns.get_indexer(['km'])].values) - 
                           (df.iloc[v, df.columns.get_indexer(['km'])].values))
            # from kilometers to meters
            distance = distance * 1000 
            # assign distance as weight to edge
            G[u][v]['weight'] = distance
    
    # return network
    return G

# call function
bridge_network()