import pandas as pd, json

noised = pd.read_csv("noised_dataset.csv")
normal = noised[noised["Label"] == 0]


with open("baseline_feature_order.json") as f:
    feature_order = json.load(f)

stats = normal[feature_order].agg(["mean", "std"]).to_dict()
with open("nominal_baseline_stats.json", "w") as f:
    json.dump(stats, f, indent=2)
