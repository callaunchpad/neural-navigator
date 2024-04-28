import logging
import time

import pandas as pd
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

class TrainTestGenerator:
    def __init__(self: str):
        pass

    def prepare_data(self):
        df_user_interactions = pd.read_csv("data/full_interaction.csv").drop(columns=["Unnamed: 0"])      
        return df_user_interactions

    def forward_chaining(self): # no timestamp in data
        data = self.prepare_data()

        values = [0.3, 0.2, 0.1]
        
        for test_sample_size in values:
            train_df, test_df = train_test_split(data, test_size=test_sample_size, random_state=42) # 42 for reproducability

            yield test_sample_size, train_df, test_df

def compute_ranks(train, test, recommended):
    train = train.copy()
    test = test.copy()
    recommended = recommended.copy()

    # Remove train items from recommended
    # Items seen in train will not be recommended to users
    for item in train:
        if item in recommended:
            recommended.remove(item)

    ranks = []

    # Iterate through all test items
    for item in test:
        try:
            rank = recommended.index(item) + 1  # Indices start with 0, ranks with 1
        except ValueError:
            # Item was not seen in train set
            rank = None
        finally:
            ranks.append(rank)
    return ranks


def compute_normalized_ranks(train, test, recommended):
    train = train.copy()
    test = test.copy()
    recommended = recommended.copy()

    # Remove train items from recommended
    # Items seen in train will not be recommended to users
    for item in train:
        if item in recommended:
            recommended.remove(item)

    ranks = []

    # Iterate through all test items
    for item in test:
        try:
            rank = recommended.index(item) + 1  # Indices start with 0, ranks with 1
        except ValueError:
            # Item was not seen in train set
            rank = None
        else:
            recommended.remove(item)
        finally:
            ranks.append(rank)
    return ranks


def hit_rate_at_k(ranks, k):
    ranks = pd.Series(ranks)
    hits_at_k = ranks <= k
    hits_at_k = hits_at_k.sum()
    hit_rate = hits_at_k / len(ranks)

    return hit_rate


def mean_reciprocal_rank(ranks):
    # TODO How to deal with nans - items not in train set
    ranks = pd.Series(ranks)
    mrr = (1 / ranks).mean()

    return mrr


def recall_at_k(ranks, k):
    ranks = pd.Series(ranks)
    recall = (ranks <= k).sum() / len(ranks)

    return recall


class Stopwatch:
    def __init__(self):
        self.start_times = {}
        self.times = {}

    def start(self, tag):
        self.start_times[tag] = time.time()

    def stop(self, tag):
        self.times[tag] = time.time() - self.start_times[tag]

    def get_df(self):
        df = pd.DataFrame(self.times.items(), columns=["tag", "time"])
        return df

    def set_from_df(self, times_df):
        self.times = times_df.set_index("tag")["time"].to_dict()


class Evaluator:
    def __init__(self, model_init, train_test_generator: TrainTestGenerator):
        self.model_init = model_init
        self.train_test_generator = train_test_generator
        self.stopwatch = Stopwatch()
        self.results = pd.DataFrame()

    def evaluate(self):
        results = []

        # test_year --> sample_size
        
        for sample_size, train, test in self.train_test_generator.forward_chaining():
            logging.info(f"Test sample size: {sample_size}")

            # Init model
            self.stopwatch.start(f"model_init_{sample_size}")
            model = self.model_init() # NOTE
            self.stopwatch.stop(f"model_init_{sample_size}")

            # Fit model
            self.stopwatch.start(f"model_fit_{sample_size}")
            model.fit(train)
            self.stopwatch.stop(f"model_fit_{sample_size}")

            # Evaluate model
            n_items = len(train["user_id"].unique())

            for user_id in test["user_id"].unique(): # iterate over unique test users
                user_train = list(train.loc[train["user_id"] == user_id, "user_id"]) # get all instances of test user in train set
                user_test = list(test[test["user_id"] == user_id]["user_id"]) # get all instances of test user in test set

                # Recommend items to a user
                self.stopwatch.start(f"recommend_user_{sample_size}_{user_id}")
                recommended = list(model.recommend(user_id, n_items))
                self.stopwatch.stop(f"recommend_user_{sample_size}_{user_id}")

                # Compute normalized ranks
                # TODO Compute recall@k
                ranks = compute_ranks(user_train, user_test, recommended)
                norm_ranks = compute_normalized_ranks(user_train, user_test, recommended)
                results_user = pd.DataFrame({
                    "user": user_id,
                    "item": user_test,
                    "ranks": ranks,
                    "norm_ranks": norm_ranks,
                    "sample_size": sample_size
                })
                results.append(results_user)
        self.results = pd.concat(results).reset_index(drop=True)

    def get_hit_rates(self, Ks: list = None):
        if Ks is None:
            Ks = [5, 10, 25, 50, 500]

        results = self.results
        results_df = []
        sample = sorted(results["sample_size"].unique())
        for sample in samples:
            results_sample = results[results["sample_size"] == sample]
            cases = len(results_sample)
            row = [cases]
            for k in Ks:
                hr = hit_rate_at_k(results_sample["norm_ranks"], k)
                row.append(hr)
            results_df.append(row)
        results_df = pd.DataFrame(results_df, columns=["cases"] + Ks, index=samples)

        return results_df

    def get_mrr(self):
        results = self.results
        results_df = []
        samples = sorted(results["sample"].unique())
        for sample in samples:
            results_sample = results[results["sample"] == sample]
            ranks = results_sample["norm_ranks"].dropna()
            cases = len(ranks)
            mrr = mean_reciprocal_rank(ranks)
            row = [cases, mrr]
            results_df.append(row)
        results_df = pd.DataFrame(results_df, columns=["cases", "mrr"], index=samples)

        return results_df

    def get_recalls(self, Ks: list = None):
        if Ks is None:
            Ks = [5, 10, 25, 50, 500]

        results = self.results
        results_df = []
        samples = sorted(results["sample_size"].unique())
        for sample in samples:
            results_sample = results[results["sample_size"] == sample]
            cases = len(results_sample)
            row = [cases]
            for k in Ks:
                recall = recall_at_k(results_sample["ranks"], k)
                row.append(recall)
            results_df.append(row)
        results_df = pd.DataFrame(results_df, columns=["cases"] + Ks, index=samples)

        return results_df

    def get_raw_times(self):
        df = self.stopwatch.get_df()
        return df

    def get_times(self):
        df = self.stopwatch.get_df()
        df["task"] = df["tag"].str.split("_").str[0:2].str.join("_")
        df = df.groupby("task")["time"].describe()

        return df

    def get_fit_per_sample_times(self):
        df = self.get_raw_times()
        df["task"] = df["tag"].str.split("_").str[0:2].str.join("_")
        df = df.set_index("task")
        return df.loc["model_fit"]

    def save_results(self, ranks_path=None, times_path=None):
        """

        :param ranks_path: ranks in CSV file
        :param times_path: times in CSV file
        :return:
        """
        if ranks_path is not None:
            self.results.to_csv(ranks_path, index=False)
        if times_path is not None:
            self.get_raw_times().to_csv(times_path, index=False)

    def load_results(self, ranks_path=None, times_path=None):
        """

        :param ranks_path: ranks in CSV file
        :return:
        """
        if ranks_path is not None:
            self.results = pd.read_csv(ranks_path)
        if times_path is not None:
            self.stopwatch.set_from_df(pd.read_csv(times_path))
