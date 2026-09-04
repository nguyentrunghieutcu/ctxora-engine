"""Local TF-IDF + LSA embedding engine."""

from __future__ import annotations

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import Normalizer

_DIM = 128


class EmbeddingEngine:
    """Local LSA-based embedding engine (TF-IDF → SVD → L2-normalise)."""

    def __init__(self, dim: int = _DIM):
        self.dim = dim
        self._corpus: list[str] = []
        self._pipe: Pipeline | None = None

    def _fit(self, texts: list[str]) -> None:
        n_components = min(self.dim, len(texts) - 1) if len(texts) > 1 else 1
        self._pipe = Pipeline([
            ("tfidf", TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                max_features=20_000,
                sublinear_tf=True,
            )),
            ("svd", TruncatedSVD(n_components=n_components, random_state=42)),
            ("norm", Normalizer(copy=False)),
        ])
        self._pipe.fit(texts)

    def _transform(self, texts: list[str]) -> np.ndarray:
        if self._pipe is None:
            return np.zeros((len(texts), self.dim), dtype=np.float32)

        vecs = self._pipe.transform(texts).astype(np.float32)
        if vecs.shape[1] < self.dim:
            pad = np.zeros(
                (vecs.shape[0], self.dim - vecs.shape[1]), dtype=np.float32)
            vecs = np.hstack([vecs, pad])
        return vecs[:, : self.dim]

    def rebuild(self, texts: list[str]) -> list[list[float]]:
        """Fit once against the complete corpus and return aligned vectors.

        LSA components change whenever the corpus changes. Rebuilding all vectors
        together prevents the vector store from comparing embeddings from two
        incompatible bases.
        """
        self._corpus = list(dict.fromkeys(texts))
        self._pipe = None
        if len(self._corpus) >= 2:
            self._fit(self._corpus)
        return self._transform(texts).tolist()

    def embed_text(self, text: str) -> list[float]:
        """Embed a query with the existing corpus model without refitting it."""
        return self._transform([text])[0].tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Compatibility wrapper for callers indexing a complete corpus."""
        if not texts:
            return []
        return self.rebuild(texts)

    def similarity(self, a: str, b: str) -> float:
        if self._pipe is None:
            self.rebuild([a, b])
        vecs = self._transform([a, b])
        dot = float(np.dot(vecs[0], vecs[1]))
        return max(-1.0, min(1.0, dot))
