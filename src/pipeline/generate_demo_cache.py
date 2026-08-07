"""
Pre-computes one full pipeline run per attack class and caches the results
to disk, so the Gradio dashboard can offer a "Demo Mode" that reviewers can
click through WITHOUT their own Groq API key and without live rate-limit
risk. This is the Week 5 "cached/rate-limit-safe demo mode" deliverable.

Run whenever you want to refresh the cached examples:
    python src/pipeline/generate_demo_cache.py
"""
import sys
import json
import time
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tools.monitor_tool import FEATURE_ORDER
from pipeline.full_pipeline import run_pipeline_for_window

CLASS_NAMES = ["Normal", "Storage Exhaustion", "Command Flooding", "Data Injection", "Defence Impairment"]
CACHE_PATH = Path(__file__).resolve().parent / "demo_cache.json"


def pick_representative_row(noised: pd.DataFrame, label: int) -> dict:
    """Picks one row for this label -- prefers a mid-confidence-band-looking
    example (not the very first row) so the demo isn't always the same
    trivial case; falls back to the first available row for that label."""
    group = noised[noised["Label"] == label]
    row = group.iloc[len(group) // 3]  # a row roughly a third into that class's block
    return {f: float(row[f]) for f in FEATURE_ORDER}


def main():
    noised = pd.read_csv(PROJECT_ROOT / "data" / "noised" / "noised_dataset.csv")

    cache = {}
    if CACHE_PATH.exists():
        cache = json.loads(CACHE_PATH.read_text())

    for label, class_name in enumerate(CLASS_NAMES):
        if class_name in cache and cache[class_name].get("status") != "ERROR":
            print(f"Skipping {class_name} -- already cached successfully.")
            continue
        if class_name in cache:
            print(f"Retrying {class_name} -- previous attempt ended in ERROR.")

        window = pick_representative_row(noised, label)
        print(f"Running full pipeline for {class_name} (true label {label})...")
        result = run_pipeline_for_window(window)

        cache[class_name] = {
            "true_label": label,
            "status": result["status"],
            "classification": (
                {"predicted_class": result["classification"].predicted_class,
                 "confidence": result["classification"].confidence}
                if result["classification"] else None
            ),
            "sparta_context": result["sparta_context"],
            "mitigation": result["mitigation"],
            "report": result["report"],
        }
        CACHE_PATH.write_text(json.dumps(cache, indent=2))
        print(f"  -> status={result['status']}, cached to {CACHE_PATH}")

        if label < len(CLASS_NAMES) - 1:
            time.sleep(45)  # same TPM-budget spacing as full_pipeline.py

    print(f"\nDone. {len(cache)}/{len(CLASS_NAMES)} classes cached in {CACHE_PATH}")


if __name__ == "__main__":
    main()
