# Imports

#!pip install cmfrec
from cmfrec import CMF_implicit # Collective Matrix Factorization Lib

import pandas as pd
from src.evaluator import Evaluator, TrainTestGenerator

# data visualization
from IPython.core.interactiveshell import InteractiveShell
InteractiveShell.ast_node_interactivity = "all"
pd.set_option('display.max_rows', 4000)

# set up data generator
data_generator = TrainTestGenerator()
interaction_df = data_generator.prepare_data()
interaction_df.head()

# model class
class CMF_recommender:
    def __init__(self, k=50):
        self.model = CMF_implicit(
            k=k,
            random_state=1,
        )

    def fit(self, data: pd.DataFrame):
        data = data.copy()

        # Binary adjacency matrix (no weights) -- look into this more...line's sketchy -- can we not encode more??
        binary_data = data[data["rating_id"] > 5] 
        binary_data["rating_id"] = 1

        print(binary_data.head())
        print(len(binary_data))

        # Rename
        binary_data = binary_data.rename(columns={
            "user_id": "UserId",
            "item_id": "ItemId",
            "rating_id": "Rating"
        })

        # Fit
        self.model.fit(binary_data)

    def recommend(self, user_id, n):
        recommendations = self.model.topN(user_id, n=n)
        return recommendations
    
evaluator = Evaluator(CMF_recommender, data_generator)
evaluator.evaluate()