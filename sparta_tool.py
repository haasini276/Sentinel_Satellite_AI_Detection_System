import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from typing import Literal
import chromadb
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

_client = chromadb.PersistentClient(path="./chroma_sparta")
_collection = _client.get_or_create_collection("sparta_knowledge")

CLASS_NAMES = ["Normal", "Storage Exhaustion", "Command Flooding", "Data Injection", "Defence Impairment"]


def get_class_mapping(class_name: str) -> dict:
    """Exact metadata lookup for a class's SPARTA mapping — deterministic, not
    semantic search, so it can never be out-competed by an unrelated document
    that happens to mention the class name (this is exactly what went wrong
    with a pure semantic search once the incident count grew)."""
    result = _collection.get(
        where={"$and": [{"type": "class_mapping"}, {"class_name": class_name}]}
    )
    if not result["documents"]:
        return {"error": f"No class mapping found for '{class_name}'"}
    return {"text": result["documents"][0], "metadata": result["metadatas"][0]}


def search_sparta_incidents(query: str, n_results: int = 2) -> list[dict]:
    """Fuzzy semantic search, restricted to incident documents only — used for
    'find a related real-world precedent' style queries, not exact class lookup."""
    results = _collection.query(
        query_texts=[query], n_results=n_results, where={"type": "incident"}
    )
    hits = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        hits.append({"text": doc, "metadata": meta})
    return hits


class ClassMappingQuery(BaseModel):
    class_name: Literal["Normal", "Storage Exhaustion", "Command Flooding", "Data Injection", "Defence Impairment"] = Field(
        ..., description="The exact detected attack class name from the Classifier Agent."
    )


class SPARTAClassMappingTool(BaseTool):
    name: str = "get_sparta_class_mapping"
    description: str = (
        "Looks up the exact SPARTA tactic/technique mapping for a detected attack "
        "class. Use this whenever you need to explain what a Classifier Agent "
        "detection means in SPARTA terms."
    )
    args_schema: type[BaseModel] = ClassMappingQuery

    def _run(self, class_name: str) -> dict:
        return get_class_mapping(class_name)


class IncidentSearchQuery(BaseModel):
    query: str = Field(..., description="A topic or keyword to find a related real-world spacecraft cyber incident for.")


class SPARTAIncidentSearchTool(BaseTool):
    name: str = "search_sparta_incidents"
    description: str = (
        "Searches only the real-world incident case studies (not class mappings) "
        "for a related precedent to a given topic or attack class."
    )
    args_schema: type[BaseModel] = IncidentSearchQuery

    def _run(self, query: str) -> list[dict]:
        return search_sparta_incidents(query)
