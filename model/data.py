import pandas as pd
import random


def convert_data():
    """
    Converts data conform demo data files.
    """

    # import data
    df = pd.read_excel('../data/bridges.xlsx')

    # slice data information
    df = df[["road", "km", "type", "name", "length", "condition", "lat", "lon", "zone"]]

    # HANDLING MISSING VALUES

    # change NaN values in name with dot i.e. '.'
    df['name'].fillna('.', inplace=True)

    # check NaN values in other columns, only length has missing values
    df.isnull().sum(axis=0)

    # assign new dataframe to missing values
    missing = df[df.length.isnull()]

    # for some missing values, missing values can be retrieved from bridges with same chainage, 
    # get length of these bridges and replace missing value with this value. 
    for index in missing.index:
        if df.loc[index, 'km'] == df.loc[index - 1, 'km']:
            # assign length of bridge with same chainage to variable new_length
            new_length = df.loc[index - 1, 'length']
            # replace missing value with new length
            df.loc[index, 'length'] = new_length

        elif df.loc[index, 'km'] == df.loc[index + 1, 'km']:
            new_length = df.loc[index + 1, 'length']
            df.loc[index, 'length'] = new_length

    # for the left-over missing values, replace length with average length of bridges for specific road
    for index in missing.index:
        road_name = df.loc[index, 'road']
        road_subset = df[df['road'] == road_name]
        average_length = road_subset.loc[:, 'length'].mean()
        df.loc[index, 'length'] = average_length

    # HANDLING DUPLICATES

    # change type of column first
    df['name'] = df['name'].astype(str)

    # replace modifications of right/left in bridge names
    df['name'] = df['name'].apply(lambda x: x.replace(')', ''))
    df['name'] = df['name'].apply(lambda x: x.replace('RIGHT', 'R'))
    df['name'] = df['name'].apply(lambda x: x.replace('LEFT', 'L'))
    df['name'] = df['name'].apply(lambda x: x.replace('Right', 'R'))
    df['name'] = df['name'].apply(lambda x: x.replace('Left', 'L'))

    # strip the trailing whitespaces 
    df['name'] = df['name'].apply(lambda x: x.strip())

    # define dataframe for duplicates
    duplicaterows = df[df['road'] == 'N1']
    # subset based on latitude and longitude
    duplicaterows = duplicaterows[duplicaterows.duplicated(subset=['lat', 'lon'])]
    # sort by chainage
    duplicaterows.sort_values(by=['km'])
    # change condition from letters to numbers in order to compare them
    df['conditionNum'] = 0
    df.loc[df['condition'] == 'A', 'conditionNum'] = 1
    df.loc[df['condition'] == 'B', 'conditionNum'] = 2
    df.loc[df['condition'] == 'C', 'conditionNum'] = 3
    df.loc[df['condition'] == 'D', 'conditionNum'] = 4

    for road in df.road:
        # define dataframe for duplicates
        road_subset = df[df['road'] == road]
        # subset based on latitude and longitude
        duplicates = road_subset[road_subset.duplicated(subset=['lat', 'lon'])]
        # sort by chainage
        duplicates.sort_values(by=['km'])

        # initialize a list for indexes to remove after running for-loop
        remove_index = []

        for index in duplicates.index:
            # retrieve latitude and longitude
            latitude = df.loc[index, 'lat']
            longitude = df.loc[index, 'lon']

            # define a subset of duplicates based on the latitude and longitude
            subset = df.loc[((df['lat'] == latitude) & (df['lon'] == longitude))]

            # define lists for bridges with left, right, or neither in their name
            contains_left = []
            contains_right = []
            contains_none = []

            for index in subset.index:
                # for every row in subset, retrieve condition and assign to set
                condition = subset.loc[index, 'conditionNum']
                # define the set with both index and condition
                condition_set = (index, condition)

                # retrieve name and whether L or R in name
                name = subset.loc[index, 'name']
                last_letter = name[-1:]
                # check whether last letter is R, L, or something else
                if last_letter == 'R':
                    contains_right.append(condition_set)

                elif last_letter == 'L':
                    contains_left.append(condition_set)

                else:
                    contains_none.append(condition_set)

                    # when no left and right in name, but other letters
            if len(contains_left) == 0 and len(contains_right) == 0 and len(contains_none) > 0:
                # check whether conditions of bridges are equal
                if contains_none[0][1] == contains_none[1][1]:
                    # if so, pick random index and append to list
                    random_none = random.choice(contains_none)
                    remove_index.append(random_none[0])

                # if condition of one is greater than other, remove the highest one
                # better be safe than sorry
                elif contains_none[0][1] < contains_none[1][1]:
                    remove_index.append(contains_none[0][0])

                elif contains_none[0][1] > contains_none[1][1]:
                    remove_index.append(contains_none[1][0])

            # capitalized one is often an updated version, we assume. Hence, remove the left and right
            if len(contains_left) == 1 and len(contains_right) == 1 and len(contains_none) == 1:
                for element in contains_left:
                    remove_index.append(element[0])
                for element in contains_right:
                    remove_index.append(element[0])

            # if two times left
            if len(contains_left) == 2:
                # check whether conditions are equal
                if contains_left[0][1] == contains_left[1][1]:
                    # then randomly pick one
                    random_left = random.choice(contains_left)
                    remove_index.append(random_left[0])

                # else check which condition is better, remove that one
                elif contains_left[0][1] < contains_left[1][1]:
                    remove_index.append(contains_left[0][0])

                elif contains_left[0][1] > contains_left[1][1]:
                    remove_index.append(contains_left[1][0])

            # same structure as with left, now for right
            if len(contains_right) == 2:
                if contains_right[0][1] == contains_right[1][1]:
                    random_left = random.choice(contains_right)
                    remove_index.append(random_left[0])

                elif contains_right[0][1] < contains_right[1][1]:
                    remove_index.append(contains_right[0][0])

                elif contains_right[0][1] > contains_right[1][1]:
                    remove_index.append(contains_right[1][0])

            # if left and capital, remove left one
            if len(contains_left) == 1 and len(contains_none) == 1:
                for element in contains_left:
                    remove_index.append(element[0])

            # if right and capital, remove right one
            if len(contains_right) == 1 and len(contains_none) == 1:
                for element in contains_right:
                    remove_index.append(element[0])

            # if both right and left, keep both 
            if len(contains_right) == 1 and len(contains_left) == 1 and len(contains_none) == 0:
                continue

        # only retrieve unique indexes in list, otherwise we remove all
        used = set()
        unique_indexes = [x for x in remove_index if x not in used and (used.add(x) or True)]

        # remove all the indexes in removing list
        for element in unique_indexes:
            df = df.drop(index=element)

    # FORMAT DATAFRAME CONFORM DEMO FILES

    # add model type
    df['model_type'] = 'bridge'

    # sort values based on km and road name, in reversed direction to drive in opposite direction
    df = df.sort_values(by=['road', 'km'])

    # reset index
    df = df.reset_index()

    # drop unnecessary columns
    df = df.drop("conditionNum", axis='columns')
    df = df.drop("index", axis='columns')
    df = df.drop("zone", axis='columns')

    # convert dataframe to csv
    df.to_csv('../data/bridges_cleaned_without_sourcesink.csv')


# call function
convert_data()
