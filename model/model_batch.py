import pandas as pd
from model import BangladeshModel
from mesa import batch_run

"""
    Run simulation
    Perform batchrunner
"""

# ---------------------------------------------------------------

# Define the dictionary with scenario's
collapse_dict = [{'A': 0, 'B': 0, 'C': 0, 'D': 0},
                 {'A': 0, 'B': 0, 'C': 0, 'D': 0.05},
                 {'A': 0, 'B': 0, 'C': 0, 'D': 0.10},
                 {'A': 0, 'B': 0, 'C': 0.05, 'D': 0.10},
                 {'A': 0, 'B': 0, 'C': 0.10, 'D': 0.20},
                 {'A': 0, 'B': 0.05, 'C': 0.10, 'D': 0.20},
                 {'A': 0, 'B': 0.10, 'C': 0.20, 'D': 0.40},
                 {'A': 0.05, 'B': 0.10, 'C': 0.20, 'D': 0.40},
                 {'A': 0.10, 'B': 0.20, 'C': 0.40, 'D': 0.80}]

# Initialize the counter to insert in filename
scenario: int = 0

# Loop over the scenarios
for dictionary in collapse_dict:
    # Define the parameters that need to be assessed by the batch runner
    params = {"collapse_dict": [dictionary]}

    # Settings of batch runner
    results = batch_run(
        BangladeshModel,
        parameters=params,
        iterations=10,
        max_steps=7200,
        number_processes=1,
        data_collection_period=7200,
        display_progress=True)

    # Convert results to dataframe
    df_results = pd.DataFrame(results)
    # Convert dataframe to CSV-file
    df_results.to_csv("../experiment/scenario"+str(scenario)+".csv")

    # Add one to scenario counter
    scenario += 1
