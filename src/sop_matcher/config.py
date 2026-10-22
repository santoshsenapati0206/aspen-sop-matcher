"""Settings, read from environment variables (or a .env file in the project root)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

try:  # optional
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


@dataclass
class Settings:
    backend: str = field(default_factory=lambda: os.getenv("SOP_BACKEND", "local"))   # local | databricks
    sop_dir: Path = field(default_factory=lambda: Path(os.getenv("SOP_DIR", ROOT / "data" / "sops")))
    local_index_path: Path = field(default_factory=lambda: Path(os.getenv("LOCAL_INDEX_PATH", ROOT / ".index" / "local_index.pkl")))
    local_embedder: str = field(default_factory=lambda: os.getenv("LOCAL_EMBEDDER", "tfidf"))  # tfidf | sentence-transformers

    # Databricks AI Search (formerly Vector Search)
    databricks_host: str | None = field(default_factory=lambda: os.getenv("DATABRICKS_HOST"))
    databricks_token: str | None = field(default_factory=lambda: os.getenv("DATABRICKS_TOKEN"))
    ai_search_endpoint: str = field(default_factory=lambda: os.getenv("AI_SEARCH_ENDPOINT", "sop-search-endpoint"))
    ai_search_index: str = field(default_factory=lambda: os.getenv("AI_SEARCH_INDEX", "workspace.mlops_sop.sop_chunks_index"))
    ai_search_query_type: str = field(default_factory=lambda: os.getenv("AI_SEARCH_QUERY_TYPE", "hybrid"))  # ann | hybrid

    # Matching
    top_k_chunks: int = int(os.getenv("TOP_K_CHUNKS", "12"))
    min_confidence: float = float(os.getenv("MIN_CONFIDENCE", "0.55"))
