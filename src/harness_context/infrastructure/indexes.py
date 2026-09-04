from __future__ import annotations

from collections.abc import Sequence

from harness_context.schemas import ContextItem
from harness_context.tokenize import tokens
from retrieval.embeddings import EmbeddingEngine


class LocalSemanticIndex:
    def __init__(self, embedder: EmbeddingEngine | None = None) -> None:
        self.embedder = embedder or EmbeddingEngine(); self.vectors: list[list[float]] = []
    def rebuild(self, items: Sequence[ContextItem]) -> None: self.vectors = self.embedder.rebuild([item.content for item in items])
    def scores(self, query: str, items: Sequence[ContextItem]) -> list[float]:
        semantic = self.embedder.embed_text(query)
        return [sum(a * b for a, b in zip(vector, semantic)) for vector in self.vectors]


class LocalLexicalIndex:
    def rebuild(self, items: Sequence[ContextItem]) -> None: pass
    def scores(self, query: str, items: Sequence[ContextItem]) -> list[float]:
        query_tokens = set(tokens(query)); return [len(query_tokens & set(tokens(item.content))) / max(len(query_tokens), 1) for item in items]


class LocalSymbolIndex:
    def rebuild(self, items: Sequence[ContextItem]) -> None: pass
    def scores(self, query: str, items: Sequence[ContextItem]) -> list[float]: return [1.0 if item.symbol.casefold() in query.casefold() else 0.0 for item in items]


class LocalPathIndex:
    def rebuild(self, items: Sequence[ContextItem]) -> None: pass
    def scores(self, query: str, items: Sequence[ContextItem]) -> list[float]:
        query_tokens = set(tokens(query)); return [len(query_tokens & set(tokens(item.path))) / max(len(query_tokens), 1) for item in items]
