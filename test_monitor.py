import pandas as pd
import json
from monitor_tool import should_escalate

with open("baseline_feature_order.json") as f:
    feature_order = json.load(f)

noised = pd.read_csv("noised_dataset.csv")
for label, group in noised.groupby("Label"):
    rows = group[feature_order].to_dict("records")
    escalated = sum(should_escalate(r) for r in rows)
    print(f"Label {label}: {escalated}/{len(rows)} escalated ({escalated/len(rows):.1%})")
