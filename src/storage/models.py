"""SQLAlchemy ORM models for content deduplication and flashcard audit history."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy models."""


class SourceDocument(Base):
    """Represents a raw URL, PDF, or audio source processed by the pipeline."""

    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_identifier: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    chunks: Mapped[list[ProcessedChunk]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class ProcessedChunk(Base):
    """Stores individual text chunk hashes to prevent duplicate LLM calls."""

    __tablename__ = "processed_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"))
    chunk_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    source: Mapped[SourceDocument] = relationship(back_populates="chunks")
    cards: Mapped[list[StoredCard]] = relationship(
        back_populates="chunk", cascade="all, delete-orphan"
    )


class StoredCard(Base):
    """Persisted record of every verified Anki flashcard generated."""

    __tablename__ = "stored_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("processed_chunks.id"))
    card_id: Mapped[str] = mapped_column(String(128), index=True)
    card_type: Mapped[str] = mapped_column(String(32))
    domain: Mapped[str] = mapped_column(String(32))
    difficulty_score: Mapped[int] = mapped_column(Integer)
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    extra_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_csv: Mapped[str] = mapped_column(String(512))
    is_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    chunk: Mapped[ProcessedChunk] = relationship(back_populates="cards")