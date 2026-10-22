"""Level 0: ticket -> best SOP.

1. Build a query from the ticket.
2. Retrieve the top-k SOP chunks (local or Databricks AI Search).
3. Roll chunk scores up to SOP level, weighting by section type
   (a hit on "When to use" counts more than a hit on "Deployment").
4. Confidence = share of the winning SOP's score versus the runner-up.
   Low confidence -> NEEDS_REVIEW, so an engineer picks the SOP by hand.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field

from .retrievers import Hit, Retriever
from .ticket import Ticket


@dataclass
class SopCandidate:
    sop_id: str
    sop_title: str
    score: float
    evidence: list[dict] = field(default_factory=list)   # best-matching sections


@dataclass
class MatchResult:
    ticket_id: str
    status: str                 # MATCHED | NEEDS_REVIEW | NO_MATCH
    sop_id: str | None
    sop_title: str | None
    confidence: float
    candidates: list[SopCandidate]
    query: str

    def to_dict(self) -> dict:
        return asdict(self)


def rank_sops(hits: list[Hit]) -> list[SopCandidate]:
    by_sop: dict[str, SopCandidate] = {}
    contributions: dict[str, list[tuple[float, Hit]]] = defaultdict(list)
    for h in hits:
        if h.score <= 0 or h.weight <= 0:
            continue
        contributions[h.sop_id].append((h.score * h.weight, h))

    for sop_id, items in contributions.items():
        items.sort(key=lambda x: -x[0])
        total = sum(s for s, _ in items[:3])   # top-3 sections per SOP, so long SOPs don't win on volume
        h0 = items[0][1]
        by_sop[sop_id] = SopCandidate(
            sop_id=sop_id,
            sop_title=h0.sop_title,
            score=round(total, 4),
            evidence=[{"section": h.section, "score": round(s, 4), "snippet": h.text[:180]} for s, h in items[:3]],
        )
    return sorted(by_sop.values(), key=lambda c: -c.score)


def match_ticket(ticket: Ticket, retriever: Retriever, top_k: int = 12, min_confidence: float = 0.55) -> MatchResult:
    query = ticket.to_query()
    candidates = rank_sops(retriever.search(query, top_k))

    if not candidates:
        return MatchResult(ticket.ticket_id, "NO_MATCH", None, None, 0.0, [], query)

    best = candidates[0]
    runner_up = candidates[1].score if len(candidates) > 1 else 0.0
    confidence = round(best.score / (best.score + runner_up), 3) if best.score else 0.0
    status = "MATCHED" if confidence >= min_confidence else "NEEDS_REVIEW"
    return MatchResult(ticket.ticket_id, status, best.sop_id, best.sop_title, confidence, candidates, query)
