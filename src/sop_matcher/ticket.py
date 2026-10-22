"""Load an ASPEN ticket (JSON) and turn it into a search query.

Only the parts that describe WHAT is being asked go into the query. Requester name/email,
timestamps and IDs are left out: they add noise to retrieval and shouldn't be sent to a
search service anyway.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# request_details keys that carry no meaning for SOP selection
_SKIP_KEYS = {"owner", "cost_center", "email", "requester"}


@dataclass
class Ticket:
    ticket_id: str
    title: str
    description: str
    details: dict[str, Any]
    justification: str
    raw: dict[str, Any]

    @classmethod
    def from_file(cls, path: str | Path) -> "Ticket":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            ticket_id=raw["ticket_id"],
            title=raw.get("title", ""),
            description=raw.get("description", ""),
            details=raw.get("request_details", {}) or {},
            justification=raw.get("business_justification", ""),
            raw=raw,
        )

    def to_query(self) -> str:
        parts = [self.title, self.description]
        parts.extend(_flatten(self.details))
        parts.append(self.justification)
        return " ".join(p for p in parts if p).strip()


def _flatten(obj: Any, key: str = "") -> list[str]:
    """Render request_details as 'key value' phrases, e.g. 'principal_type group', 'type function privilege EXECUTE'."""
    if isinstance(obj, dict):
        out: list[str] = []
        for k, v in obj.items():
            if k.lower() in _SKIP_KEYS:
                continue
            out.extend(_flatten(v, k))
        return out
    if isinstance(obj, list):
        out = []
        for v in obj:
            out.extend(_flatten(v, key))
        return out
    if isinstance(obj, bool):
        return [key.replace("_", " ")] if obj else []
    return [f"{key.replace('_', ' ')} {obj}".strip()]
