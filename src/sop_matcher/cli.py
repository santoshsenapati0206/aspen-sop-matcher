"""Command line entry point.

    python -m sop_matcher index                               # build the local index from data/sops/*.pdf
    python -m sop_matcher match data/tickets/ASPEN-1001.json  # find the SOP for a ticket
    python -m sop_matcher match data/tickets/*.json --json    # machine-readable output
    python -m sop_matcher match data/tickets/ASPEN-1001.json --backend databricks
"""
from __future__ import annotations

import argparse
import json
import sys

from .chunking import chunk_folder
from .config import Settings
from .matcher import match_ticket
from .retrievers import get_retriever
from .ticket import Ticket


def cmd_index(s: Settings) -> None:
    from .retrievers.local import LocalRetriever

    chunks = chunk_folder(s.sop_dir)
    if not chunks:
        sys.exit(f"No SOP PDFs found in {s.sop_dir}")
    LocalRetriever.build(chunks, embedder=s.local_embedder).save(s.local_index_path)
    sops = sorted({c.sop_id for c in chunks})
    print(f"Indexed {len(chunks)} chunks from {len(sops)} SOPs ({', '.join(sops)}) -> {s.local_index_path}")


def cmd_match(s: Settings, paths: list[str], as_json: bool) -> None:
    retriever = get_retriever(s)
    results = [match_ticket(Ticket.from_file(p), retriever, s.top_k_chunks, s.min_confidence) for p in paths]
    if as_json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
        return
    for r in results:
        print(f"\n=== {r.ticket_id} ===")
        print(f"Status     : {r.status}")
        print(f"SOP        : {r.sop_id} - {r.sop_title}")
        print(f"Confidence : {r.confidence:.2f}")
        print("Candidates :")
        for c in r.candidates[:4]:
            print(f"   {c.sop_id:<12} score={c.score:.3f}   top section: {c.evidence[0]['section']}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="sop_matcher", description="Match ASPEN tickets to the right SOP")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index", help="Build the local search index from SOP PDFs")
    m = sub.add_parser("match", help="Find the SOP for one or more ticket JSON files")
    m.add_argument("tickets", nargs="+")
    m.add_argument("--backend", choices=["local", "databricks"])
    m.add_argument("--json", action="store_true", help="print JSON instead of a summary")
    args = p.parse_args(argv)

    s = Settings()
    if getattr(args, "backend", None):
        s.backend = args.backend
    if args.cmd == "index":
        cmd_index(s)
    else:
        cmd_match(s, args.tickets, args.json)


if __name__ == "__main__":
    main()
