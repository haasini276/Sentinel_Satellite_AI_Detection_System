import json
from pathlib import Path
import pandas as pd
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ML_DIR = Path(__file__).resolve().parent

raw = pd.read_csv(PROJECT_ROOT / "data" / "raw" / "consolidated_dataset_raw.csv")
noised = pd.read_csv(PROJECT_ROOT / "data" / "noised" / "noised_dataset.csv")

common_cols = [c for c in noised.columns if c in raw.columns and c != "Label"]
Xtr, ytr = raw[common_cols], raw["Label"]

model = xgb.XGBClassifier(
    n_estimators=150,
    max_depth=6,
    eval_metric="mlogloss",
    n_jobs=4,
    random_state=42,
)
model.fit(Xtr, ytr)

model.save_model(str(ML_DIR / "baseline_xgb.json"))

with open(ML_DIR / "baseline_feature_order.json", "w") as f:
    json.dump(common_cols, f, indent=2)

print("Saved baseline_xgb.json")
print("Saved baseline_feature_order.json")
print("Feature count:", len(common_cols))
