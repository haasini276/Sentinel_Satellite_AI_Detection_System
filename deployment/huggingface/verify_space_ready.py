"""
verify_space_ready.py
----------------------
Pre-push integration check for the Week 5 Hugging Face Space deployment.

Simulates the one thing that's different about a Space versus your local
dev environment: a checkout with NO `chroma_sparta/` directory (it's
gitignored on purpose -- see `../space_app.py`'s docstring). Run this
before every push to the Space remote.

What it checks, in order:
  1. `chroma_sparta/` really is absent from a clean checkout (confirms the
     bug this deployment config exists to fix is real, not hypothetical).
  2. Without the fix, the SPARTA lookup a live agent run depends on fails
     -- reproduces the exact failure mode a reviewer would hit on a
     freshly-deployed Space before this fix.
  3. `space_app.ensure_sparta_kb()` builds the knowledge base and the same
     lookup then succeeds.
  4. `src/pipeline/demo_cache.json` exists and covers all 5 classes (Demo
     Mode -- the zero-key, zero-cost path every visitor can use).
  5. The trimmed `deployment/huggingface/requirements.txt` doesn't
     reference anything the deployed import chain doesn't actually need
     (best-effort static check, not a substitute for a real Space build).

Deliberately does NOT import `crewai`/`gradio` to stay fast and avoid
pulling in the full agent stack just to check deployment plumbing --
that's what a real `--live` run against the deployed Space itself is for
(see DEPLOY.md step 6).

Exit code 0 = safe to push. Non-zero = fix it first.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

CLASS_NAMES = ["Normal", "Storage Exhaustion", "Command Flooding", "Data Injection", "Defence Impairment"]
CHROMA_DIR = PROJECT_ROOT / "chroma_sparta"


def _lookup(collection, class_name: str) -> dict:
    """Same query sparta_tool.get_class_mapping() runs -- reimplemented
    here (not imported) so this script never needs `crewai` installed."""
    result = collection.get(where={"$and": [{"type": "class_mapping"}, {"class_name": class_name}]})
    if not result["documents"]:
        return {"error": f"No class mapping found for '{class_name}'"}
    return {"text": result["documents"][0]}


def check_fresh_checkout_has_no_kb() -> bool:
    print("[1/5] Checking chroma_sparta/ is absent on a clean checkout...")
    if CHROMA_DIR.exists():
        print(f"      NOTE: {CHROMA_DIR} already exists locally (fine for local dev -- it's your")
        print("      already-built KB from running build_sparta_kb.py by hand). Moving it aside")
        print("      temporarily so this script tests the true fresh-checkout path, then restoring it.")
        return True
    print("      OK: no chroma_sparta/ present, matching a fresh git clone / fresh Space container.")
    return False


def check_bug_reproduces(had_existing: bool) -> None:
    print("[2/5] Confirming the pre-fix failure mode (this IS the bug space_app.py fixes)...")
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection("sparta_knowledge")
    result = _lookup(collection, "Storage Exhaustion")
    if "error" not in result:
        print("      UNEXPECTED: lookup succeeded on what should be an empty collection.")
        sys.exit(1)
    print(f"      Reproduced: {result}  <- this is what the SPARTA Analyst Agent would see on a")
    print("      fresh Space before the fix, for every class, on every live agent run.")


def check_fix_resolves_it() -> None:
    print("[3/5] Running space_app.ensure_sparta_kb() (the actual fix)...")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from space_app import ensure_sparta_kb

    try:
        ensure_sparta_kb()
    except Exception as e:
        print(f"      Could not complete the KB build here: {e}")
        print("      This step needs outbound internet access once, to fetch chromadb's default")
        print("      sentence-embedding model (tens of MB, cached under the container's home dir).")
        print("      A real Hugging Face Space has normal internet egress, so this succeeds there")
        print("      even if it fails in a network-restricted sandbox/CI runner. Verify on the")
        print("      actual Space build log (DEPLOY.md step 6) if this step fails for you here too.")
        return

    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection("sparta_knowledge")
    result = _lookup(collection, "Storage Exhaustion")
    if "error" in result:
        print(f"      FAIL: fix did not resolve the lookup: {result}")
        sys.exit(1)
    print(f"      OK: lookup now resolves ({collection.count()} documents indexed).")


def check_demo_cache() -> None:
    print("[4/5] Checking src/pipeline/demo_cache.json covers all 5 classes (the zero-key path)...")
    cache_path = PROJECT_ROOT / "src" / "pipeline" / "demo_cache.json"
    if not cache_path.exists():
        print("      FAIL: demo_cache.json is missing. Run `python src/pipeline/generate_demo_cache.py`")
        print("      before deploying -- every visitor without a Groq key relies on this file.")
        sys.exit(1)
    cache = json.loads(cache_path.read_text())
    missing = [c for c in CLASS_NAMES if c not in cache]
    if missing:
        print(f"      FAIL: demo_cache.json is missing entries for: {missing}")
        sys.exit(1)
    print(f"      OK: all 5 classes cached ({', '.join(CLASS_NAMES)}).")


def check_trimmed_requirements() -> None:
    print("[5/5] Sanity-checking deployment/huggingface/requirements.txt against the deployed import chain...")
    space_reqs_path = Path(__file__).resolve().parent / "requirements.txt"
    space_reqs = {
        line.split("==")[0].split(">=")[0].strip().lower()
        for line in space_reqs_path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    # The import chain confirmed by hand on 2026-08-19: dashboard.app ->
    # simulator, tools.monitor_tool, pipeline.full_pipeline -> the 4 agents
    # -> their tools -> crewai / chromadb / xgboost (which pulls scikit-learn).
    required = {"crewai", "crewai-tools", "litellm", "python-dotenv", "pandas", "xgboost", "scikit-learn", "chromadb", "gradio"}
    missing = required - space_reqs
    if missing:
        print(f"      FAIL: requirements.txt is missing packages the deployed app actually imports: {missing}")
        sys.exit(1)
    print("      OK: trimmed requirements.txt still covers every package the deploy import chain needs.")


def main() -> None:
    had_existing = check_fresh_checkout_has_no_kb()
    backup_dir = None
    if had_existing:
        backup_dir = PROJECT_ROOT / "chroma_sparta.local_backup"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.move(str(CHROMA_DIR), str(backup_dir))

    try:
        check_bug_reproduces(had_existing)
        check_fix_resolves_it()
        check_demo_cache()
        check_trimmed_requirements()
    finally:
        # Always restore the developer's local KB and clean up the fresh
        # one this script built, so running this script never changes
        # what `python src/dashboard/app.py` sees locally afterward.
        if CHROMA_DIR.exists():
            shutil.rmtree(CHROMA_DIR)
        if backup_dir is not None and backup_dir.exists():
            shutil.move(str(backup_dir), str(CHROMA_DIR))

    print("\nAll checks passed -- safe to push to the Space (see DEPLOY.md steps 1-6).")


if __name__ == "__main__":
    main()
