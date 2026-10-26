"""Unit tests for offline .apkg package creation and Markdown export."""

from __future__ import annotations

from pathlib import Path

from src.core.schemas import AnkiCard
from src.export.anki_package import AnkiPackageExporter
from src.export.markdown import MarkdownExporter


def test_apkg_file_generation(tmp_path: Path, sample_atomic_card: AnkiCard) -> None:
    exporter = AnkiPackageExporter(deck_name="Test::Deck")
    out_file = tmp_path / "test_deck.apkg"
    saved = exporter.export_to_file([sample_atomic_card], out_file)
    assert saved.exists()
    assert saved.stat().st_size > 0


def test_markdown_export(tmp_path: Path, sample_atomic_card: AnkiCard) -> None:
    md_exporter = MarkdownExporter(deck_name="Test::Deck")
    out_md = tmp_path / "notes.md"
    saved = md_exporter.export_to_file([], [sample_atomic_card], out_md, thought_process="Test reasoning")
    assert saved.exists()
    content = saved.read_text(encoding="utf-8")
    assert "In PostgreSQL WAL" in content