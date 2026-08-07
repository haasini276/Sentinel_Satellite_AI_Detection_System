import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd
import json
from tools.monitor_tool import should_escalate

with open(PROJECT_ROOT / "src" / "ml" / "baseline_feature_order.json") as f:
    feature_order = json.load(f)

noised = pd.read_csv(PROJECT_ROOT / "data" / "noised" / "noised_dataset.csv")
for label, group in noised.groupby("Label"):
    rows = group[feature_order].to_dict("records")
    escalated = sum(should_escalate(r) for r in rows)
    print(f"Label {label}: {escalated}/{len(rows)} escalated ({escalated/len(rows):.1%})")
