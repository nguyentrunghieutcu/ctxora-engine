from __future__ import annotations

import re
import unicodedata


def tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", text)
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", normalized).replace("_", " ")
    words = re.findall(r"[^\W_]+", normalized.casefold(), re.UNICODE)
    grams = [word[index:index + 3] for word in words for index in range(max(0, len(word) - 2))]
    return words + grams
