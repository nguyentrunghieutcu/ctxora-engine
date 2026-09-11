from rank_bm25 import BM25Okapi

from harness_context.infrastructure.retrieval.tokenize import tokenize


class BM25Index:
    def __init__(self):
        self.bm25 = None
        self.chunks = []

    def build(self, chunks: list):
        self.chunks = chunks
        if not chunks:
            self.bm25 = None
            return
        tokenized_corpus = [tokenize(c.content) for c in chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def score(self, query: str) -> list[float]:
        if not self.bm25:
            return []
        tokenized_query = tokenize(query)
        return self.bm25.get_scores(tokenized_query).tolist()
