from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Chunk:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[Chunk]:
    words = text.split()
    if not words:
        return []

    chunk_size = max(chunk_size, 1)
    overlap = min(max(overlap, 0), chunk_size - 1) if chunk_size > 1 else 0
    step = max(chunk_size - overlap, 1)

    chunks: list[Chunk] = []
    for start in range(0, len(words), step):
        window = words[start : start + chunk_size]
        if not window:
            break
        chunks.append(
            Chunk(
                content=" ".join(window),
                metadata={"start_word": start, "end_word": start + len(window)},
            )
        )
    return chunks


class Chunker:
    def chunk(self, text: str, chunk_size: int = 600, overlap: int = 100) -> list[Chunk]:
        return chunk_text(text, chunk_size=chunk_size, overlap=overlap)
