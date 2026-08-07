import pandas as pd, json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ML_DIR = Path(__file__).resolve().parent

noised = pd.read_csv(PROJECT_ROOT / "data" / "noised" / "noised_dataset.csv")
normal = noised[noised["Label"] == 0]


with open(ML_DIR / "baseline_feature_order.json") as f:
    feature_order = json.load(f)

stats = normal[feature_order].agg(["mean", "std"]).to_dict()
with open(ML_DIR / "nominal_baseline_stats.json", "w") as f:
    json.dump(stats, f, indent=2)
