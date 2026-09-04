class EccService:
    def __init__(self, reader): self.reader = reader
    def status(self): return self.reader.status() if self.reader else {"enabled": False, "available": False, "read_only": True}
    def search(self, query, limit=4):
        if self.reader is None or not self.reader.installation.available:
            raise ValueError("ECC adapter is not enabled or no local ECC vault was detected")
        return self.reader.search(query, limit)
