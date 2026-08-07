import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tools.mitigation_tool import decide_mitigation

tests = [
    ("Storage Exhaustion", 0.849), ("Storage Exhaustion", 0.85),
    ("Storage Exhaustion", 0.699), ("Storage Exhaustion", 0.70),
    ("Command Flooding", 0.84), ("Command Flooding", 0.85),
    ("Command Flooding", 0.69), ("Command Flooding", 0.70),
    ("Data Injection", 0.849), ("Data Injection", 0.85),
    ("Data Injection", 0.699), ("Data Injection", 0.70),
    ("Defence Impairment", 0.699), ("Defence Impairment", 0.70),
]

for cls, conf in tests:
    r = decide_mitigation(cls, conf)
    print(f"{cls:20s} {conf:.3f} -> {r['action']}")
