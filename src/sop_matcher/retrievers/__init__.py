from __future__ import annotations

from ..config import Settings
from .base import Hit, Retriever


def get_retriever(settings: Settings) -> Retriever:
    if settings.backend == "local":
        from .local import LocalRetriever
        return LocalRetriever.load(settings.local_index_path)
    if settings.backend == "databricks":
        from .databricks_ai_search import DatabricksAISearchRetriever
        return DatabricksAISearchRetriever(
            host=settings.databricks_host,
            token=settings.databricks_token,
            endpoint=settings.ai_search_endpoint,
            index_name=settings.ai_search_index,
            query_type=settings.ai_search_query_type,
        )
    raise ValueError(f"Unknown backend '{settings.backend}' (use 'local' or 'databricks')")


__all__ = ["Hit", "Retriever", "get_retriever"]
