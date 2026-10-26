"""Unit tests for YouTube ID extraction and PDF text chunking."""

from __future__ import annotations

import pytest

from src.core.exceptions import IngestionError
from src.ingestion.pdf import PDFIngestor
from src.ingestion.youtube import YouTubeIngestor


def test_extract_youtube_id() -> None:
    url_standard = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    url_short = "https://youtu.be/dQw4w9WgXcQ?si=12345"
    assert YouTubeIngestor.extract_video_id(url_standard) == "dQw4w9WgXcQ"
    assert YouTubeIngestor.extract_video_id(url_short) == "dQw4w9WgXcQ"


def test_invalid_youtube_url_raises() -> None:
    with pytest.raises(IngestionError):
        YouTubeIngestor.extract_video_id("https://example.com/not-a-video")


def test_pdf_chunking() -> None:
    ingestor = PDFIngestor(chunk_size=50, chunk_overlap=10)
    text = "A" * 100
    chunks = ingestor.chunk_text(text)
    assert len(chunks) == 3
    assert all(len(c) <= 50 for c in chunks)