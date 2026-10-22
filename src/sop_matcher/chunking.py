"""Turn SOP PDFs into section-level chunks.

One chunk = one numbered section of one SOP. Each chunk carries the SOP id/title so
the retriever can score it and the matcher can roll scores back up to the SOP.

This module has no Databricks dependency, so the same code runs on your laptop and in a
Databricks notebook (01_ingest_sops.py imports it from the Git folder).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

SOP_ID_RE = re.compile(r"\b(SOP-[A-Z]+-\d{3})\b")
SECTION_RE = re.compile(r"^(\d{1,2})\.\s+([A-Z][^\n]{2,80})$")
BULLET_RE = re.compile(r"^[-••]\s*$")

# How much each section type should count when ranking SOPs.
# "Scope"/"When to use" describe WHAT the SOP is for; implementation details matter less;
# "Not covered" mentions OTHER SOPs' topics, so it must not pull the ranking toward itself.
SECTION_WEIGHTS = {
    "purpose and scope": 1.0,
    "when to use this sop": 1.0,
    "required information in the ticket": 0.6,
    "validation rules": 0.4,
    "approval": 0.3,
    "implementation": 0.3,
    "deployment": 0.2,
    "post-deployment verification": 0.2,
    "not covered by this sop": 0.0,
}
DEFAULT_WEIGHT = 0.4


@dataclass
class Chunk:
    chunk_id: str
    sop_id: str
    sop_title: str
    section_no: int
    section: str
    weight: float
    text: str          # text that gets embedded/indexed (includes SOP title + section as context)
    source_file: str

    def to_dict(self) -> dict:
        return asdict(self)


def extract_text(pdf_path: str | Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _clean(lines: Iterable[str]) -> str:
    """Drop bullet-only lines and join wrapped lines into readable sentences."""
    kept = [ln.strip() for ln in lines if ln.strip() and not BULLET_RE.match(ln.strip())]
    return re.sub(r"\s+", " ", " ".join(kept)).strip()


def chunk_sop(pdf_path: str | Path) -> list[Chunk]:
    pdf_path = Path(pdf_path)
    text = extract_text(pdf_path)
    lines = text.splitlines()

    m = SOP_ID_RE.search(text)
    if not m:
        raise ValueError(f"No SOP id (SOP-XXX-NNN) found in {pdf_path.name}")
    sop_id = m.group(1)

    # Header = everything before the first numbered section; title = header minus id/owner line.
    first_sec = next((i for i, ln in enumerate(lines) if SECTION_RE.match(ln.strip())), len(lines))
    header = _clean(ln for ln in lines[:first_sec] if not ln.strip().lower().startswith("owner:"))
    sop_title = header.split(":", 1)[1].strip() if ":" in header else header

    chunks: list[Chunk] = []
    current_no, current_name, buf = None, None, []

    def flush():
        if current_no is None:
            return
        body = _clean(buf)
        if not body:
            return
        weight = SECTION_WEIGHTS.get(current_name.lower(), DEFAULT_WEIGHT)
        chunks.append(Chunk(
            chunk_id=f"{sop_id}::{current_no:02d}",
            sop_id=sop_id,
            sop_title=sop_title,
            section_no=current_no,
            section=current_name,
            weight=weight,
            text=f"{sop_title}. {current_name}: {body}",
            source_file=pdf_path.name,
        ))

    for ln in lines[first_sec:]:
        sec = SECTION_RE.match(ln.strip())
        if sec:
            flush()
            current_no, current_name, buf = int(sec.group(1)), sec.group(2).strip(), []
        else:
            buf.append(ln)
    flush()
    return chunks


def chunk_folder(folder: str | Path) -> list[Chunk]:
    out: list[Chunk] = []
    for pdf in sorted(Path(folder).glob("*.pdf")):
        out.extend(chunk_sop(pdf))
    return out
