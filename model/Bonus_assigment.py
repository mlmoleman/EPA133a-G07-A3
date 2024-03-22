import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as cx
from shapely import distance
from pyproj import Transformer
from shapely.geometry import LineString, MultiPoint
import shapely.ops as sp_ops
import warnings
import os
from shapely import buffer
from shapely import wkt

import matplotlib.lines as mlines

os.environ['USE_PYGEOS'] = '0'
warnings.filterwarnings("ignore")

# Gets the path to the main folder
main_folder_path = os.path.normpath(os.getcwd() + os.sep + os.pardir)
# Reads the road data
df = gpd.read_file(main_folder_path + "/data/gis/osm/roads.shp")
# Selects all the unique values in the ref column
road_names = df[df["ref"].notnull()]["ref"].unique()
# Select the rows that start with an N, indicating the N roads
road_names_N = [road for road in road_names if road.startswith("N")]

# Subsets a dataframe wit hall the N road data
df_N = df[df["ref"].isin(road_names_N)]
# Removes the spaces between the N and the number in some rows
df_N["ref"] = df_N["ref"].str.replace(" ", "")

# Creates a dataframe that contains the road sections for the N1 and N2
df_primary = df[(df["type"] == "primary") | (df["type"] == "trunk")]
# Gets the intersections that are calculated for the main model
df_sections = pd.read_csv(main_folder_path + "/data/intersections_BONUS.csv")
# Convert the geometry back into working shapely geometry
df_sections["geometry"] = df_sections["geometry"].apply(wkt.loads)
# Turns the df into a gdf
df_sections = gpd.GeoDataFrame(df_sections, geometry="geometry", crs="EPSG:4326")

# Will contain buffered versions of the intersections
points = []
# Loops over all the intersection points
for point in df_sections["geometry"]:
    point = buffer(point, 0.1)
    points.append(point)

# Removes the spaces between the N and the number in some rows
df_primary["ref"] = df_primary["ref"].str.replace(" ", "")

# Subsets a dataframe for only the N1 and N2
df_N1N2 = df_primary[(df_primary["ref"] == "N1") | (df_primary["ref"] == "N2")]

# Loads in the road data and turns it into a geopandas dataframe
df_normal_data = pd.read_csv(main_folder_path + "/data/_roads3.csv")
gdf_normal = gpd.GeoDataFrame(df_normal_data, geometry=gpd.points_from_xy(df_normal_data.lon, df_normal_data.lat),
                              crs="EPSG:4326")

# Will contain the lines of the N1 and N2
lines = []
# Loops over the N1 and N2 name
for name in ["N1", "N2"]:
    # Subsets for the road
    gdf_temp = gdf_normal[gdf_normal["road"] == name]
    # Buffers the line
    line = buffer(LineString(gdf_temp["geometry"]), 0.1)
    # Puts into the list
    lines.append(line)

# Will contain the index of the lines that intersects with the buffered N1 or N2
cross_index_N1 = []
cross_index_N2 = []
# Loops over all the primary nad trunk roads
for index in df_primary.index:
    # Check if the road intersects with the N1
    if lines[0].intersects(df_primary.loc[index, "geometry"]):
        # If yes add to the list
        cross_index_N1.append(index)
    # Check if the road intersects with the N2
    if lines[1].intersects(df_primary.loc[index, "geometry"]):
        # If yes add to the list
        cross_index_N2.append(index)

# Select the lines that intersect with the N1 and N2
intersecting_N1 = df_primary[df_primary.index.isin(cross_index_N1)]
intersecting_N2 = df_primary[df_primary.index.isin(cross_index_N2)]
# Merge the lines for the N1 and N2 into one dataframe
intersecting_N1N2 = pd.concat([intersecting_N1, intersecting_N2])
# Removes the Spaces and all the segments of the N1 and N2 itself
intersecting_N1N2 = intersecting_N1N2[~intersecting_N1N2["ref"].str.replace(" ", "").isin(["N1", "N2"])]

# Will contain the intersection points calculated with the shapefile
Intersect_points = []
# Loops over the lines segements of the N1 and N2
for line_N1N2 in df_N1N2["geometry"]:
    # loops over the lines that intersect with the N1 and N2
    for intersect_line in intersecting_N1N2["geometry"]:
        # If the segments are not the same
        if line_N1N2 != intersect_line:
            # If the lines intersect
            if line_N1N2.intersects(intersect_line):
                # Calcualte the intersection point
                Intersect_points.append(line_N1N2.intersection(intersect_line))

# Makes and GeoSeries from the points that intersect with the N1 and N2
shape_file_intersects = gpd.GeoSeries(Intersect_points, crs="4326")

# Will contain the pairs of the intersection points based on the csv data and shapefile data
final_pair = []

# Loops over the intersections of the csv data
for section in df_sections["geometry"]:
    # Indicates the smallest distance
    min_dist = 10000
    # Loops over the all the intersection points of the shapefile data
    for shape_file_intersect in shape_file_intersects.unique():
        # Checks if there are multiple intersections
        if isinstance(shape_file_intersect, MultiPoint):
            # If yes, it will loop over the multiple intersections
            for point in list(shape_file_intersect.geoms):
                # Calculate distance
                dist = distance(section, point)
                # Check if it is smaller then the already smallest distance
                if dist < min_dist:
                    # If yes, update the current smallest distance
                    min_dist = dist
                    # Change the current pair that have the smallest distance
                    closest_point_pair = (section, point)
        # If there are no multiple intersections
        else:
            # Calculate distance
            dist = distance(section, shape_file_intersect)
            # If yes, update the current smallest distance
            if dist < min_dist:
                # If yes, update the current smallest distance
                min_dist = dist
                # Change the current pair that have the smallest distance
                closest_point_pair = (section, shape_file_intersect)
    # After looping over every combination, the pair with the smallest distance is added to the list
    final_pair.append(closest_point_pair)

# Will contain the lengths that is between the intersection points
# from the csv data and the intersection points from the shapefile
dict_length = {}
# Transformer that can convert to another crs
transformer = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True)
# Loops over the pairs
for index, pair in enumerate(final_pair):
    # Turns  the pair into a line
    line = LineString([pair[0], pair[1]])
    # Converts the line to crs that uses meters and then calculates the distance
    line_length = sp_ops.transform(transformer.transform, line).length
    # Add the distance with its road name to the dict
    dict_length[df_sections["Unnamed: 0"][index]] = line_length / 1000

# Defines the grid in which the plots will be placed
fig, ax = plt.subplots(3, 4, figsize=(10, 10))
# Turn the 3x4 axis matris into a 1X12 one
ax = ax.flatten()
# Will contain the length between every pair of points
dict_length = {}
# Labels for the legend
orginal = mlines.Line2D([], [], color='red', marker='s', ls='', label='Csv data')
shapefile = mlines.Line2D([], [], color='blue', marker='D', ls='', label='Shapefile data')

bar_index=[]
# Loops over the pair
for index, pair in enumerate(final_pair):
    # Creates a linestring between the points in the pair
    line = LineString([pair[0], pair[1]])
    # Converse the crs to one with meters instead of lon,lat
    line_length = sp_ops.transform(transformer.transform, line).length
    print(line_length)
    # Plots the points
    gpd.GeoSeries(pair[0], crs="EPSG:4326").plot(ax=ax[index], color="red")
    gpd.GeoSeries(pair[1], crs="EPSG:4326").plot(ax=ax[index], color="blue")
    # Plots line between the points
    gpd.GeoSeries(line, crs="EPSG:4326").plot(ax=ax[index], color="white")

    # Plots an invicible circle around the points and line. This makes the size of the plot the same
    gpd.GeoSeries(buffer(line.centroid, 0.03), crs="EPSG:4326").plot(ax=ax[index], color="pink", alpha=0)
    # Adds a map to the plot
    cx.add_basemap(ax=ax[index], crs="EPSG:4326", attribution_size=0)
    # Adds a legend under the 9th plot
    if index == 8:
        ax[index].legend(handles=[orginal, shapefile], loc="lower center", bbox_to_anchor=(0.0, -0.4, 0.0, 0.0))
    # Creates the title with the road name and distance
    ax[index].title.set_text((df_sections["intersec_to"][index], f"{int(line_length)} m"))
    # Puts the road with the length in the dict
    bar_index.append(df_sections["intersec_to"][index])
    dict_length[df_sections["intersec_to"][index]] = line_length / 1000
plt.savefig(main_folder_path + "/img/bonus_pair.png")
plt.show()

# Creates a bar plot
plt.bar(bar_index, dict_length.values(), color="red")
# Create correct axis labels and title
plt.xlabel("Road to which the N1 or N2 connects")
plt.ylabel("Difference in kilometers")
plt.title("Difference intersections shapefile and csv", fontsize=14)
plt.savefig(main_folder_path + "/img/bonus_bar.png")
plt.show()
