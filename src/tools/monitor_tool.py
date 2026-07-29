import json
from crewai.tools import BaseTool
from pydantic import BaseModel, create_model

with open("nominal_baseline_stats.json") as f:
    STATS = json.load(f)

with open("baseline_feature_order.json") as f:
    FEATURE_ORDER = json.load(f)


def should_escalate(window: dict, z_thresh: float = 5.0, min_features: int = 1) -> bool:
    tripped = 0
    for feature, value in window.items():
        mean = STATS[feature]["mean"]
        std = STATS[feature]["std"]
        if std == 0:
            continue
        z = abs(value - mean) / std
        if z > z_thresh:
            tripped += 1
    return tripped >= min_features


MonitorWindow = create_model(
    "MonitorWindow",
    **{f: (float, ...) for f in FEATURE_ORDER},
)


class MonitorTool(BaseTool):
    name: str = "check_escalation"
    description: str = (
        "Checks whether a telemetry window deviates enough from nominal "
        "baseline behavior to warrant escalating to the Classifier Agent."
    )
    args_schema: type[BaseModel] = MonitorWindow

    def _run(self, **window) -> dict:
        return {"escalate": should_escalate(window)}

