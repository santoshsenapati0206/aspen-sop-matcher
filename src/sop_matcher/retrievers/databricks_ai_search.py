"""Databricks AI Search backend (the product formerly called Vector Search).

The index is a Delta Sync index over the `sop_chunks` Delta table, with embeddings
computed by Databricks (see databricks/01_ingest_sops.py). Querying needs only the
workspace URL and a personal access token, so it works from your laptop too.

SDK: `pip install databricks-ai-search` (new name). The legacy `databricks-vectorsearch`
package exposes the same API, so either is accepted here.
"""
from __future__ import annotations

from .base import CHUNK_COLUMNS, Hit, Retriever


def _client(host: str | None, token: str | None):
    try:
        from databricks.ai_search.client import AISearchClient as Client
    except ImportError:
        try:
            from databricks.vector_search.client import VectorSearchClient as Client
        except ImportError as e:
            raise ImportError("Install the SDK: pip install databricks-ai-search") from e

    if host and token:
        return Client(workspace_url=host, personal_access_token=token, disable_notice=True)
    return Client(disable_notice=True)  # inside a Databricks notebook credentials are auto-detected


class DatabricksAISearchRetriever(Retriever):
    def __init__(self, host: str | None, token: str | None, endpoint: str, index_name: str, query_type: str = "hybrid"):
        self.index = _client(host, token).get_index(endpoint_name=endpoint, index_name=index_name)
        self.query_type = query_type

    def search(self, query: str, k: int) -> list[Hit]:
        resp = self.index.similarity_search(
            query_text=query,
            columns=CHUNK_COLUMNS,
            num_results=k,
            query_type=self.query_type,
        )
        # Response shape: {"manifest": {"columns": [{"name": ...}, ...]}, "result": {"data_array": [[...], ...]}}
        # The last column is the relevance score.
        cols = [c["name"] for c in resp["manifest"]["columns"]]
        hits = []
        for row in resp.get("result", {}).get("data_array", []) or []:
            r = dict(zip(cols, row))
            hits.append(Hit(
                chunk_id=r["chunk_id"], sop_id=r["sop_id"], sop_title=r["sop_title"], section=r["section"],
                weight=float(r["weight"]), score=float(row[-1]), text=r["text"],
            ))
        return hits
