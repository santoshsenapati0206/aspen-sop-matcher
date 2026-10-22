"""Laptop backend: no cloud needed.

Default embedder is TF-IDF (word 1-2 grams), which needs nothing beyond scikit-learn.
Set LOCAL_EMBEDDER=sentence-transformers to blend in dense embeddings
(all-MiniLM-L6-v2, ~90 MB download on first run). With both, the score is a 50/50 blend,
which behaves like Databricks AI Search's `hybrid` query type.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ..chunking import Chunk
from .base import Hit, Retriever

DENSE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class LocalRetriever(Retriever):
    def __init__(self, chunks: list[dict], vectorizer: TfidfVectorizer, tfidf_matrix, dense: np.ndarray | None, embedder: str):
        self.chunks = chunks
        self.vectorizer = vectorizer
        self.tfidf_matrix = tfidf_matrix
        self.dense = dense
        self.embedder = embedder
        self._model = None

    # ---------- build / persist ----------
    @classmethod
    def build(cls, chunks: list[Chunk], embedder: str = "tfidf") -> "LocalRetriever":
        rows = [c.to_dict() for c in chunks]
        texts = [r["text"] for r in rows]
        vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
        matrix = vec.fit_transform(texts)
        dense = None
        if embedder == "sentence-transformers":
            dense = _dense_model().encode(texts, normalize_embeddings=True)
        return cls(rows, vec, matrix, dense, embedder)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"chunks": self.chunks, "vectorizer": self.vectorizer, "tfidf": self.tfidf_matrix,
                         "dense": self.dense, "embedder": self.embedder}, f)

    @classmethod
    def load(cls, path: Path) -> "LocalRetriever":
        if not path.exists():
            raise FileNotFoundError(f"No local index at {path}. Run: python -m sop_matcher index")
        with open(path, "rb") as f:  # only load index files you built yourself
            d = pickle.load(f)
        return cls(d["chunks"], d["vectorizer"], d["tfidf"], d["dense"], d["embedder"])

    # ---------- search ----------
    def search(self, query: str, k: int) -> list[Hit]:
        q = self.vectorizer.transform([query])
        scores = (self.tfidf_matrix @ q.T).toarray().ravel()   # tf-idf rows are L2-normalised -> cosine
        if self.dense is not None:
            if self._model is None:
                self._model = _dense_model()
            qd = self._model.encode([query], normalize_embeddings=True)[0]
            scores = 0.5 * scores + 0.5 * (self.dense @ qd)
        top = np.argsort(-scores)[:k]
        return [
            Hit(chunk_id=c["chunk_id"], sop_id=c["sop_id"], sop_title=c["sop_title"], section=c["section"],
                weight=float(c["weight"]), score=float(scores[i]), text=c["text"])
            for i in top
            for c in [self.chunks[i]]
        ]


def _dense_model():
    from sentence_transformers import SentenceTransformer  # optional dependency
    return SentenceTransformer(DENSE_MODEL)
