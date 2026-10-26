"""Unit tests for Pydantic schema validation rules."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.schemas import AnkiCard, CardEvaluation, CardType, CognitiveDomain


def test_valid_anki_card(sample_atomic_card: AnkiCard) -> None:
    assert sample_atomic_card.card_id == "wal_001"
    assert sample_atomic_card.difficulty_score == 2
    assert sample_atomic_card.evaluation.is_atomic is True


def test_difficulty_score_bounds() -> None:
    with pytest.raises(ValidationError):
        AnkiCard(
            card_id="bad_001",
            card_type=CardType.BASIC,
            domain=CognitiveDomain.FACTUAL,
            difficulty_score=9,
            front="What is X?",
            back="Y",
            tags=["test::tag"],
            evaluation=CardEvaluation(is_atomic=True, has_leakage=False),
        )