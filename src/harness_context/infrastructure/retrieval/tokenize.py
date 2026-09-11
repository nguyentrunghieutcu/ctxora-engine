from __future__ import annotations

import re
import unicodedata


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text).replace("_", " ")
    words = re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE)
    return words + [word[index:index + 3] for word in words for index in range(max(0, len(word) - 2))]
