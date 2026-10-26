"""Data access repository for SHA-256 content deduplication and card persistence."""

from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.schemas import AnkiCard, CardEvaluation, CardType, CognitiveDomain
from src.storage.models import ProcessedChunk, SourceDocument, StoredCard


class StorageRepository:
    """Manages deduplication checks and persistence of generated flashcards."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def compute_hash(text: str) -> str:
        """Compute a deterministic SHA-256 hex digest of normalized text."""
        normalized = " ".join(text.strip().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def is_chunk_processed(self, raw_text: str) -> bool:
        """Return True if a chunk with the identical SHA-256 hash already exists."""
        chunk_hash = self.compute_hash(raw_text)
        stmt = select(ProcessedChunk.id).where(ProcessedChunk.chunk_hash == chunk_hash)
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def get_cards_by_chunk(self, raw_text: str) -> list[AnkiCard]:
        """Retrieve previously generated AnkiCard schemas for a cached chunk."""
        chunk_hash = self.compute_hash(raw_text)
        stmt = select(ProcessedChunk).where(ProcessedChunk.chunk_hash == chunk_hash)
        chunk: ProcessedChunk | None = self.session.execute(stmt).scalar_one_or_none()
        if not chunk:
            return []

        return [
            AnkiCard(
                card_id=sc.card_id,
                card_type=CardType(sc.card_type),
                domain=CognitiveDomain(sc.domain),
                difficulty_score=sc.difficulty_score,
                front=sc.front,
                back=sc.back,
                extra_context=sc.extra_context or "",
                tags=[t for t in sc.tags_csv.split(",") if t],
                evaluation=CardEvaluation(is_atomic=True, has_leakage=False),
            )
            for sc in chunk.cards
        ]

    def save_processed_chunk(
        self,
        source_identifier: str,
        source_type: str,
        raw_text: str,
        cards: list[AnkiCard],
        is_synced: bool = True,
    ) -> ProcessedChunk:
        """Persist the source record, chunk hash, and generated cards."""
        chunk_hash = self.compute_hash(raw_text)

        stmt = select(SourceDocument).where(
            SourceDocument.source_identifier == source_identifier
        )
        source_doc = self.session.execute(stmt).scalar_one_or_none()
        if not source_doc:
            source_doc = SourceDocument(
                source_identifier=source_identifier,
                source_type=source_type,
                content_hash=chunk_hash,
            )
            self.session.add(source_doc)
            self.session.flush()

        chunk_record = ProcessedChunk(
            source_id=source_doc.id,
            chunk_hash=chunk_hash,
            raw_text=raw_text,
        )
        self.session.add(chunk_record)
        self.session.flush()

        for card in cards:
            stored = StoredCard(
                chunk_id=chunk_record.id,
                card_id=card.card_id,
                card_type=card.card_type.value,
                domain=card.domain.value,
                difficulty_score=card.difficulty_score,
                front=card.front,
                back=card.back,
                extra_context=card.extra_context,
                tags_csv=",".join(card.tags),
                is_synced=is_synced,
            )
            self.session.add(stored)

        self.session.flush()
        return chunk_record