import json
from pathlib import Path
import xgboost as xgb
from crewai.tools import BaseTool
from pydantic import BaseModel, create_model

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ML_DIR = PROJECT_ROOT / "src" / "ml"


class ClassificationResult(BaseModel):
    predicted_class: str
    confidence: float

_model = xgb.XGBClassifier()
_model.load_model(str(ML_DIR / "baseline_xgb.json"))

with open(ML_DIR / "baseline_feature_order.json") as f:
    FEATURE_ORDER = json.load(f)

CLASS_NAMES = ["Normal", "Storage Exhaustion", "Command Flooding", "Data Injection", "Defence Impairment"]


def classify_telemetry(window: dict) -> dict:
    x = [[window[f] for f in FEATURE_ORDER]]
    label = int(_model.predict(x)[0])
    proba = _model.predict_proba(x)[0]
    return {"class": CLASS_NAMES[label], "confidence": round(float(proba[label]), 4)}


TelemetryWindow = create_model(
    "TelemetryWindow",
    **{f: (float, ...) for f in FEATURE_ORDER},
)


class ClassifyTelemetryTool(BaseTool):
    name: str = "classify_telemetry"
    description: str = (
        "Classifies a satellite telemetry window into Normal or one of 4 "
        "SPARTA-mapped attack classes (Storage Exhaustion, Command Flooding, "
        "Data Injection, Defence Impairment), returning the class and a "
        "confidence score."
    )
    args_schema: type[BaseModel] = TelemetryWindow

    def _run(self, **window) -> dict:
        return classify_telemetry(window)
