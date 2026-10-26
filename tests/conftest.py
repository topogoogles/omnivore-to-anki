"""Shared pytest fixtures for Omnivore-to-Anki unit tests."""

from __future__ import annotations

import pytest

from src.core.schemas import (
    AnkiCard,
    CardEvaluation,
    CardType,
    CognitiveDomain,
    DeckGenerationBatch,
    ExtractionStep,
)


@pytest.fixture
def sample_atomic_card() -> AnkiCard:
    return AnkiCard(
        card_id="wal_001",
        card_type=CardType.BASIC,
        domain=CognitiveDomain.CONCEPTUAL,
        difficulty_score=2,
        front="In PostgreSQL WAL, what must occur before dirty pages are flushed to disk?",
        back="Changes must first be written sequentially to the Write-Ahead Log.",
        extra_context="Guarantees crash recovery durability.",
        tags=["db::postgres", "storage::wal"],
        evaluation=CardEvaluation(is_atomic=True, has_leakage=False),
    )


@pytest.fixture
def sample_cloze_card() -> AnkiCard:
    return AnkiCard(
        card_id="wal_002",
        card_type=CardType.CLOZE,
        domain=CognitiveDomain.FACTUAL,
        difficulty_score=1,
        front="In PostgreSQL, {{c1::Write-Ahead Logging (WAL)}} ensures durability prior to page flushes.",
        back="Write-Ahead Logging (WAL)",
        extra_context="",
        tags=["db::postgres"],
        evaluation=CardEvaluation(is_atomic=True, has_leakage=False),
    )


@pytest.fixture
def sample_deck_batch(sample_atomic_card: AnkiCard, sample_cloze_card: AnkiCard) -> DeckGenerationBatch:
    return DeckGenerationBatch(
        thought_process="Extracting core durability guarantees of PostgreSQL WAL.",
        extracted_assertions=[
            ExtractionStep(
                source_quote="Write-Ahead Logging (WAL) ensures data integrity by writing changes to a log first.",
                core_assertion="PostgreSQL logs changes to WAL before modifying disk pages.",
                why_retrieval_matters="Core mechanism of ACID durability.",
            )
        ],
        cards=[sample_atomic_card, sample_cloze_card],
    )