from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from typing import Any

@dataclass(slots=True)
class Chunk:
    content: str
    chunk_type: str = "child"
    id: str | None = None
    parent_id: str | None = None
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
                id=str(uuid.uuid4()),
                chunk_type="child",
                metadata={"start_word": start, "end_word": start + len(window)},
            )
        )
    return chunks

class Chunker:
    def chunk(self, text: str, chunk_size: int = 600, overlap: int = 100) -> list[Chunk]:
        return chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    def chunk_parent_child(self, text: str, parent_size: int = 1500, child_size: int = 300, overlap: int = 50) -> list[Chunk]:
        all_chunks: list[Chunk] = []
        
        parent_chunks = chunk_text(text, chunk_size=parent_size, overlap=0)
        
        for parent in parent_chunks:
            parent.chunk_type = "parent"
            # Ensure parent has ID since child references it
            parent.id = parent.id or str(uuid.uuid4())
            all_chunks.append(parent)
            
            children = chunk_text(parent.content, chunk_size=child_size, overlap=overlap)
            for child in children:
                child.chunk_type = "child"
                child.parent_id = parent.id
                all_chunks.append(child)
                
        return all_chunks
