"""MCP tool helper for extracting transcripts from YouTube or local audio files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.ingestion.audio import LocalAudioTranscriber
from src.ingestion.pdf import PDFIngestor
from src.ingestion.youtube import YouTubeIngestor


def fetch_source_transcript(source: str) -> dict[str, Any]:
    """Detect whether source is a YouTube URL, PDF, or audio file and extract text."""
    if source.startswith(("http://", "https://", "www.", "youtu")):
        ingestor = YouTubeIngestor()
        return ingestor.ingest(source)

    path = Path(source)
    if path.suffix.lower() == ".pdf":
        pdf_ingestor = PDFIngestor()
        return pdf_ingestor.ingest(path)

    if path.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}:
        transcriber = LocalAudioTranscriber()
        text = transcriber.transcribe_file(path)
        return {
            "source_path": str(path.resolve()),
            "ingestion_method": "faster_whisper_local",
            "raw_text": text,
        }

    if path.exists() and path.is_file():
        return {
            "source_path": str(path.resolve()),
            "ingestion_method": "plain_text_file",
            "raw_text": path.read_text(encoding="utf-8"),
        }

    return {
        "source_path": "inline_text",
        "ingestion_method": "inline_string",
        "raw_text": source,
    }