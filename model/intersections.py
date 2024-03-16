# Import packages
import os

os.environ['USE_PYGEOS'] = '0'
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as cx
from shapely.geometry import Point, LineString, shape
import numpy as np
from shapely import distance

###
### Importing road data
###

# Selects the correct file path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
path_road = os.path.join(project_root, 'data', '_roads3.csv')

# opens csv file as df and the converts it to a geodataframe
df = pd.read_csv(path_road)
gdf = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")

###
###
###

###
### Create LineStrings from all the N roads.
###

# Filters all the different road names and picks the ones starting with a N
road_names = gdf["road"].unique()
road_names_N1 = [road for road in road_names if road.startswith("N")]

# Dictionary will contain the linestrings with the road name as key
line_dict = {}
# Loops over all the road names
for road_name in road_names_N1:
    # Selects the rows that correspond to the road name
    bridges_road = gdf[gdf["road"] == road_name]
    # Only considers roads with two or more points, can not make a line from 1 point
    if len(bridges_road["geometry"]) >= 2:
        # Creates a line from the points and add them
        line_dict[road_name] = LineString(bridges_road["geometry"])
# Turns the dictionary into a geopandas series
gseries = gpd.GeoSeries(line_dict.values(), index=line_dict.keys(), crs=4326)

###
###
###

###
### Checks which roads intersect with the N1 or N2
###


# Will contain the road names that intersect with the N1
cross_index_N1 = []
# Loops over all the lines of the roads
for index in gseries.index:
    # If the road intersects then it will add it to list
    if gseries["N1"].intersects(gseries[index]):
        cross_index_N1.append(index)

# Same as above but then for the N2
cross_index_N2 = []
for index in gseries.index:
    if gseries["N2"].intersects(gseries[index]):
        cross_index_N2.append(index)

# Select the lines that intersect with the N1 and N2
intersecting_N1 = gseries[gseries.index.isin(cross_index_N1)]
intersecting_N2 = gseries[gseries.index.isin(cross_index_N2)]

# Calculates the coordinates where the roads intersect
intersections_N1 = gseries["N1"].intersection(intersecting_N1).drop("N1")
intersections_N2 = gseries["N2"].intersection(intersecting_N2).drop("N2")

# Creates gdf's with the rows corresponding to the N1 and N2
gdf_N1 = gdf[gdf["road"] == "N1"]
gdf_N2 = gdf[gdf["road"] == "N2"]

###
###
###

###
### Gets the closest LRP on the N1 to the intersection of the two roads
###

# Will contain the rows of the points on the N1 closest the intersection
df_list = []
road_name_list = []
# Will contain the indexes of the points on the N1 closest the intersection
closest_points = []
# Loop over the needed data for the N1 and then the N2
for gdf_data, intersect_data in [[gdf_N1, intersections_N1], [gdf_N2, intersections_N2]]:
    # Loops over the the intersection point indexes
    for intersect_index_N1 in intersect_data.index:
        # Gets the point corresponding to the index
        intersect_point_N1 = intersect_data[intersect_index_N1]
        # Defines the distance between the intersection point and the closest point
        min_dist = 10000
        # Loops over the the N road point indexes
        for N_index in gdf_data.index:
            # Gets the point corresponding to the index
            N_point = gdf_data.loc[N_index, "geometry"]
            # Calculates the distance between the two points
            dist = distance(N_point, intersect_point_N1)
            # Checks if distance is smaller then the smallest value already found, if True updates the smallest
            # distance and current closest point
            if dist < min_dist:
                min_dist = dist
                closest_point = N_index
        # Add the index of the examined road
        road_name_list.append(intersect_index_N1)
        # Add the id of the closest point
        closest_points.append(closest_point)

# Uses the indexes to get the rows corresponding to the closest rows and puts it in a list
df_list.append(gdf[gdf.index.isin(closest_points)])
# Creates one dataframe from the df_list
df_intersections_main = pd.concat(df_list, axis=0, ignore_index=True)
# Adds a column with the road names to which the intersection belongs
df_intersections_main["intersec_to"] = road_name_list
# Updates the type of the points
df_intersections_main["type"] = "intersection"
# Saves the df

output_csv_path = os.path.join(project_root, 'data', 'intersections_main.csv')
df_intersections_main.to_csv(output_csv_path, index=False)

###
###
###

###
### Gets the closest LRP on the roads that intersect with the N1 and N2
###

# Will contain the rows of the points on the N1 closest the intersection
df_list = []
# Loops over the road names that intersect with the N1
for road_name in intersections_N1.index:
    # Selects the rows corresponding to the road name
    road_gdf = gdf[gdf["road"] == road_name]
    # Gets the point of the intersection
    intersect_point_N1 = intersections_N1[road_name]
    # Defines the distance between the intersection point and the closest point
    min_dist = 10000
    # Loops over the point indexes that correspond to the road that intersects with the N1
    for road_point_index in road_gdf.index:
        # Gets the point corresponding to the index
        road_point = road_gdf.loc[road_point_index, "geometry"]
        # Calculates the distance between the two points
        dist = distance(intersect_point_N1, road_point)
        # Checks if distance is smaller than the smallest value already found, if True updates the smallest
        # distance and current closest point
        if dist < min_dist:
            min_dist = dist
            closest_point = road_point_index
    # Gets the row corresponding to the closest point
    df_list.append(road_gdf[road_gdf.index == closest_point])

# Works the same as code above but then for the N2
for road_name in intersections_N2.index:
    road_gdf = gdf[gdf["road"] == road_name]
    intersect_point_N2 = intersections_N2[road_name]
    min_dist = 10000
    for road_point_index in road_gdf.index:
        road_point = road_gdf.loc[road_point_index, "geometry"]
        dist = distance(intersect_point_N2, road_point)
        if dist < min_dist:
            min_dist = dist
            closest_point = road_point_index
    #Adds the the row to the same list use for the N1
    df_list.append(road_gdf[road_gdf.index == closest_point])


#Merges the rows into a dataframe
df_intersections_side = pd.concat(df_list, axis=0, ignore_index=True)
#Updates the type column
df_intersections_side["type"] = "intersection"

output_csv_path = os.path.join(project_root, 'data', 'intersections_side.csv')
df_intersections_side.to_csv(output_csv_path, index=False)