"""Agent state definitions for the LangGraph evaluation and generation cycle."""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict

from src.core.schemas import AnkiCard, ExtractionStep


class QualityIssue(TypedDict):
    """Detailed critique of a flawed card to guide self-correction."""

    card_id: str
    issue_type: str  # 'atomicity_violation', 'answer_leakage', 'syntax_error', 'ambiguity'
    feedback: str
    suggested_fix: str


class AgentState(TypedDict, total=False):
    """State dictionary shared across all LangGraph nodes."""

    # Ingestion context
    raw_text: str
    deck_name: str
    metadata: dict[str, Any]

    # Reasoning and Extraction
    thought_process: str
    extracted_assertions: list[ExtractionStep]

    # Card lifecycle
    draft_cards: list[AnkiCard]
    rejected_issues: list[QualityIssue]
    iteration_count: int
    max_retries: int

    # Final approved output
    final_cards: list[AnkiCard]
    export_summary: dict[str, Any] | None