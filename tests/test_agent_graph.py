"""Unit tests for the LangGraph evaluator quality gate and router."""

from __future__ import annotations

import pytest

from src.agents.graph import evaluator_node, router_condition
from src.core.schemas import AnkiCard, CardEvaluation, CardType, CognitiveDomain


@pytest.mark.asyncio
async def test_evaluator_accepts_valid_cards(sample_atomic_card: AnkiCard) -> None:
    state = {"draft_cards": [sample_atomic_card]}
    result = await evaluator_node(state)
    assert len(result["final_cards"]) == 1
    assert len(result["rejected_issues"]) == 0


@pytest.mark.asyncio
async def test_evaluator_rejects_broken_cloze() -> None:
    bad_cloze = AnkiCard(
        card_id="bad_cloze_1",
        card_type=CardType.CLOZE,
        domain=CognitiveDomain.FACTUAL,
        difficulty_score=2,
        front="Cloze text without deletion syntax.",
        back="target",
        tags=["test::cloze"],
        evaluation=CardEvaluation(is_atomic=True, has_leakage=False),
    )
    state = {"draft_cards": [bad_cloze]}
    result = await evaluator_node(state)
    assert len(result["final_cards"]) == 0
    assert len(result["rejected_issues"]) == 1
    assert result["rejected_issues"][0]["issue_type"] == "syntax_error"


def test_router_logic() -> None:
    state_retry = {
        "rejected_issues": [{"card_id": "1", "issue_type": "syntax_error", "feedback": "", "suggested_fix": ""}],
        "iteration_count": 0,
        "max_retries": 2,
    }
    assert router_condition(state_retry) == "refine_node"

    state_clean = {"rejected_issues": [], "iteration_count": 0, "max_retries": 2}
    assert router_condition(state_clean) == "export_node"