from app.rag.chunker import chunk_text


def test_chunk_text_splits_text() -> None:
    chunks = chunk_text("one two three four five six", chunk_size=3, overlap=1)

    assert len(chunks) >= 2
    assert chunks[0].content.startswith("one two three")
