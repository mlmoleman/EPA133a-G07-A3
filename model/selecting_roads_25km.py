import pandas as pd


path_i = '../data/intersections_side.csv'
path_m = '../data/_roads3.csv'

df_intersections = pd.read_csv(path_i)
df_main = pd.read_csv(path_m)

roads = df_intersections['road']

roads_selection = []
for road in roads:
    road_df = df_main[df_main['road'] == road]
    if road_df.iloc[-1, 1] >= 25:
        roads_selection.append(road)

print(roads_selection)