"""Run: pytest -q   (builds a local TF-IDF index from data/sops, no cloud needed)"""
import json
from pathlib import Path

import pytest

from sop_matcher.chunking import chunk_folder
from sop_matcher.matcher import match_ticket
from sop_matcher.retrievers.local import LocalRetriever
from sop_matcher.ticket import Ticket

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def retriever():
    return LocalRetriever.build(chunk_folder(ROOT / "data" / "sops"))


def test_every_sop_is_chunked():
    chunks = chunk_folder(ROOT / "data" / "sops")
    assert {c.sop_id for c in chunks} == {"SOP-UC-001", "SOP-SP-002", "SOP-SP-003", "SOP-MDL-004"}
    assert all(c.text and c.section for c in chunks)


@pytest.mark.parametrize("ticket_file, expected", [
    ("ASPEN-1001.json", "SOP-UC-001"),
    ("ASPEN-1002.json", "SOP-SP-002"),
])
def test_sample_tickets(retriever, ticket_file, expected):
    r = match_ticket(Ticket.from_file(ROOT / "data" / "tickets" / ticket_file), retriever)
    assert r.sop_id == expected
    assert r.status == "MATCHED"


# Extra phrasings, to check the near-neighbour SOPs are told apart (SP-002 vs SP-003, UC-001 vs MDL-004)
@pytest.mark.parametrize("title, description, expected", [
    ("Run job as existing service principal",
     "Please add my group to the Service Principal User role on sp-fraud-scoring so we can run workflows as it.",
     "SOP-SP-003"),
    ("Access to churn model serving endpoint",
     "Our app needs CAN_QUERY on the model serving endpoint churn-model-prod to call it for real-time inference.",
     "SOP-MDL-004"),
    ("Write access to sales schema",
     "Grant MODIFY on table sales.gold.daily_orders to group grp-sales-eng in dev.",
     "SOP-UC-001"),
])
def test_neighbouring_sops(tmp_path, retriever, title, description, expected):
    p = tmp_path / "t.json"
    p.write_text(json.dumps({"ticket_id": "T", "title": title, "description": description}))
    assert match_ticket(Ticket.from_file(p), retriever).sop_id == expected
