"""Deterministic subword-style tokenizer mapping prompts into neural token IDs."""

from __future__ import annotations

import hashlib
import re


class NeuralTokenizer:
    """Deterministic hash-projected tokenizer for PyTorch, TensorFlow, and Keras tensors."""

    TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[^\sA-Za-z0-9_]")

    def __init__(self, vocab_size: int = 2048) -> None:
        self.vocab_size = vocab_size

    def tokenize(self, text: str) -> list[str]:
        """Split input text into word and punctuation tokens."""
        return self.TOKEN_PATTERN.findall(text.strip())

    def encode(self, text: str, max_length: int = 64) -> list[int]:
        """Encode text into bounded integer token IDs."""
        tokens = self.tokenize(text)[:max_length]
        if not tokens:
            return [1]
        ids: list[int] = []
        for tok in tokens:
            digest = hashlib.blake2b(tok.lower().encode("utf-8"), digest_size=4).digest()
            token_id = 2 + (int.from_bytes(digest, "big") % (self.vocab_size - 2))
            ids.append(token_id)
        return ids

    def count_tokens(self, text: str) -> int:
        """Estimate token count for quota and telemetry accounting."""
        return max(1, len(self.tokenize(text)))

