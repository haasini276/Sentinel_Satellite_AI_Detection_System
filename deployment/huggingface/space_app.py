"""
space_app.py
------------
Hugging Face Spaces entrypoint (Week 5 — Hardening, Software/Integration Lead).

This is NOT a rewrite of the dashboard. It's a thin cold-start wrapper around
the real app (`src/dashboard/app.py`) that fixes one concrete deployment bug
found while preparing this Space:

    `chroma_sparta/` (the SPARTA RAG knowledge base) is in .gitignore --
    correctly, since it's a generated binary ChromaDB store and shouldn't be
    committed. Locally that's fine because the setup docs tell you to run
    `python src/rag/build_sparta_kb.py` once by hand (README.md step 3).

    A fresh Hugging Face Space has no shell step for that -- it just clones
    the repo and runs the app file. Without this wrapper, `chroma_sparta/`
    would never get built on the Space, `sparta_tool.get_class_mapping()`
    would silently return `{"error": "No class mapping found for ..."}` for
    every class, and the SPARTA Analyst Agent would degrade quietly the
    first time a reviewer clicks "Run Full Agent Analysis" live (Demo Mode
    is unaffected -- it replays `demo_cache.json` and never touches Chroma).

This wrapper builds the KB once at cold start if it's missing/empty, then
launches the exact same `demo` Blocks object `src/dashboard/app.py` already
defines. No agent/dashboard logic is duplicated or forked here.

Space config (see ../README.md for the copy-pasteable frontmatter):
    sdk: gradio
    app_file: deployment/huggingface/space_app.py   (relative to repo root)

Required secret (Space Settings -> Variables and secrets):
    GROQ_API_KEY   -- only needed for the live "Run Full Agent Analysis"
                      button and the `--live` pipeline. Demo Mode and the
                      passive telemetry stream work with zero key.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))


def ensure_sparta_kb() -> None:
    """Build the SPARTA ChromaDB knowledge base if this is a fresh checkout
    (fresh Space container, fresh clone, or a wiped local chroma_sparta/).
    Idempotent and cheap (~11 short documents, no LLM calls, no network
    beyond what chromadb itself needs) -- safe to run on every cold start."""
    import os

    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    import chromadb

    client = chromadb.PersistentClient(path=str(PROJECT_ROOT / "chroma_sparta"))
    collection = client.get_or_create_collection("sparta_knowledge")

    if collection.count() == 0:
        print("[space_app] chroma_sparta/ is empty -- building SPARTA knowledge base...")
        from rag.build_sparta_kb import main as build_kb

        build_kb()
        print(f"[space_app] SPARTA knowledge base ready ({collection.count()} documents).")
    else:
        print(f"[space_app] SPARTA knowledge base already present ({collection.count()} documents) -- skipping build.")


def main() -> None:
    ensure_sparta_kb()

    # Re-export the exact same Gradio app the local dashboard uses -- no
    # forked UI logic, so this Space stays identical in behavior to
    # `python src/dashboard/app.py`. Imported here (not at module level) so
    # that `ensure_sparta_kb` alone stays importable -- e.g. by
    # verify_space_ready.py -- without pulling in gradio/crewai just to
    # test the KB cold-start fix in isolation.
    from dashboard.app import demo

    demo.queue().launch()


# Hugging Face's "gradio" SDK runs app_file as a script (`python app.py`),
# not as an imported module, so this always executes when the Space starts
# -- same pattern as `python src/dashboard/app.py` locally.
if __name__ == "__main__":
    main()
