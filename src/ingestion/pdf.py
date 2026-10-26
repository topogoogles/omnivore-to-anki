"""PDF document extractor and text cleaner using pypdf."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from src.core.exceptions import IngestionError
from src.ingestion.base import BaseSourceLoader

logger = logging.getLogger(__name__)


class PDFIngestor(BaseSourceLoader):
    """Loads PDF documents, strips layout noise, and chunks text for LLM extraction."""

    def __init__(self, chunk_size: int = 4000, chunk_overlap: int = 300) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalize whitespace, fix hyphenated line-breaks, and strip control chars."""
        text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def chunk_text(self, text: str) -> list[str]:
        """Split cleaned text into overlapping character chunks."""
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end].strip())
            start += self.chunk_size - self.chunk_overlap
        return [c for c in chunks if c]

    def ingest(self, source: str | Path, **kwargs: Any) -> dict[str, Any]:
        """Extract all pages from a PDF file and return full text plus chunks."""
        pdf_path = Path(source)
        if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
            raise IngestionError(f"Invalid or missing PDF file: {pdf_path}")

        try:
            reader = PdfReader(str(pdf_path))
            pages_text: list[str] = []
            for page in reader.pages:
                extracted = page.extract_text() or ""
                if extracted.strip():
                    pages_text.append(self._clean_text(extracted))

            full_text = "\n\n".join(pages_text)
            if not full_text:
                raise IngestionError(f"No extractable text found in PDF: {pdf_path}")

            chunks = self.chunk_text(full_text)
            logger.info(
                "Extracted %d pages (%d chunks) from %s",
                len(reader.pages),
                len(chunks),
                pdf_path.name,
            )

            return {
                "source_path": str(pdf_path.resolve()),
                "ingestion_method": "pypdf_extractor",
                "page_count": len(reader.pages),
                "raw_text": full_text,
                "chunks": chunks,
            }
        except IngestionError:
            raise
        except Exception as err:
            raise IngestionError(f"Failed to parse PDF {pdf_path}: {err}") from err