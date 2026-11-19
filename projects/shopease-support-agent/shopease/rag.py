"""Hybrid retrieval over the policy docs: BM25 + (optional) embeddings, fused with RRF, optional rerank.

BM25 always works offline. Embeddings/reranking use `fastembed` (small ONNX models, CPU) and are
skipped automatically if the models can't be downloaded.
"""
from __future__ import annotations

import re
from functools import lru_cache

from . import config

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def load_chunks() -> list[dict]:
    """One chunk per '## section' of each policy file, prefixed with its doc title (cheap contextualization)."""
    chunks = []
    for path in sorted(config.POLICY_DIR.glob("*.md")):
        text = path.read_text()
        title = text.splitlines()[0].lstrip("# ").strip()
        for section in re.split(r"\n(?=## )", text):
            body = section.strip()
            if body.startswith("# ") and "\n## " not in body and len(body.splitlines()) <= 1:
                continue  # skip a bare title
            heading = body.splitlines()[0].lstrip("# ").strip()
            chunks.append({"source": f"{path.name}#{heading}", "text": f"[{title}] {body}"})
    return chunks


@lru_cache(maxsize=1)
def _index():
    from rank_bm25 import BM25Okapi

    chunks = load_chunks()
    bm25 = BM25Okapi([tokenize(c["text"]) for c in chunks])
    return chunks, bm25


@lru_cache(maxsize=1)
def _embeddings():
    """Returns (model, matrix) or None if fastembed/models are unavailable."""
    try:
        import numpy as np
        from fastembed import TextEmbedding

        chunks, _ = _index()
        model = TextEmbedding(EMBED_MODEL)
        matrix = np.array(list(model.embed([c["text"] for c in chunks])))
        return model, matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
    except Exception as e:  # offline, blocked download, missing package...
        print(f"[rag] embeddings unavailable ({type(e).__name__}); using BM25 only")
        return None


def rrf(*rankings: list[int], k: int = 60) -> list[int]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, 1):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)


def search(query: str, k: int = 3, mode: str = "hybrid", rerank: bool = False, candidates: int = 10) -> list[dict]:
    """mode: 'bm25' | 'vector' | 'hybrid'. Returns [{source, text, score}]."""
    chunks, bm25 = _index()
    bm_scores = bm25.get_scores(tokenize(query))
    bm_rank = sorted(range(len(chunks)), key=lambda i: -bm_scores[i])[:candidates]
    ranking = bm_rank
    emb = _embeddings() if mode in ("vector", "hybrid") else None
    if emb:
        model, matrix = emb
        import numpy as np

        q = np.array(list(model.embed([query])))[0]
        sims = matrix @ (q / np.linalg.norm(q))
        vec_rank = sorted(range(len(chunks)), key=lambda i: -sims[i])[:candidates]
        ranking = vec_rank if mode == "vector" else rrf(bm_rank, vec_rank)
    ranking = ranking[:candidates]
    if rerank:
        try:
            scores = list(_reranker().rerank(query, [chunks[i]["text"] for i in ranking]))
            ranking = [i for _, i in sorted(zip(scores, ranking), key=lambda p: -p[0])]
        except Exception as e:
            print(f"[rag] rerank unavailable ({type(e).__name__})")
    return [{"source": chunks[i]["source"], "text": chunks[i]["text"], "score": float(bm_scores[i])}
            for i in ranking[:k]]


def reset_index() -> None:
    """Call after changing config.POLICY_DIR or the policy files."""
    _index.cache_clear()
    _embeddings.cache_clear()


@lru_cache(maxsize=1)
def _reranker():
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    return TextCrossEncoder(RERANK_MODEL)
