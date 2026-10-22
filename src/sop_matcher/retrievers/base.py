from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

# Columns every backend stores/returns for a chunk
CHUNK_COLUMNS = ["chunk_id", "sop_id", "sop_title", "section_no", "section", "weight", "text", "source_file"]


@dataclass
class Hit:
    chunk_id: str
    sop_id: str
    sop_title: str
    section: str
    weight: float
    score: float
    text: str


class Retriever(ABC):
    """A search backend over SOP chunks."""

    @abstractmethod
    def search(self, query: str, k: int) -> list[Hit]:
        ...
