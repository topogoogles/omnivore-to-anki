"""Pydantic validation schemas for Chain-of-Thought extraction and Anki flashcards."""

from enum import Enum

from pydantic import BaseModel, Field


class CardType(str, Enum):
    BASIC = "basic"
    CLOZE = "cloze"
    CONCEPT_PAIR = "concept_pair"


class CognitiveDomain(str, Enum):
    FACTUAL = "factual"
    CONCEPTUAL = "conceptual"
    PROCEDURAL = "procedural"


class ExtractionStep(BaseModel):
    source_quote: str = Field(
        ...,
        description="Verbatim text fragment from the source material establishing grounding.",
    )
    core_assertion: str = Field(
        ...,
        description="The atomic technical fact, definition, or relationship stripped of filler.",
    )
    why_retrieval_matters: str = Field(
        ...,
        description="Brief justification of why this fact requires active recall testing.",
    )


class CardEvaluation(BaseModel):
    is_atomic: bool = Field(
        ...,
        description="True if the card tests exactly ONE discrete memory anchor.",
    )
    has_leakage: bool = Field(
        ...,
        description="True if the question implicitly gives away the answer.",
    )
    distractor_justification: str | None = Field(
        default=None,
        description="Analysis of plausible misconceptions related to this concept.",
    )


class AnkiCard(BaseModel):
    card_id: str = Field(
        ...,
        description="Deterministic slug or hash identifier (e.g., 'cr_mem_001').",
    )
    card_type: CardType = Field(
        ...,
        description="Anki note type target: basic (Q&A), cloze (fill-in-the-blank), or concept_pair.",
    )
    domain: CognitiveDomain = Field(
        ...,
        description="Cognitive category of the tested memory item.",
    )
    difficulty_score: int = Field(
        ...,
        ge=1,
        le=5,
        description="Target difficulty level (1 = basic recall, 5 = edge-case synthesis).",
    )
    front: str = Field(
        ...,
        description=(
            "Question or prompt. For cloze types, wrap the deletion target in {{c1::target}}. "
            "Must be unambiguous, self-contained, and free of vague referents (e.g., 'this process')."
        ),
    )
    back: str = Field(
        ...,
        description="Concise, verified factual answer. Direct and focused without unasked prose.",
    )
    extra_context: str | None = Field(
        default="",
        description="Optional markdown explanation, gotchas, or mnemonic context shown after answering.",
    )
    tags: list[str] = Field(
        ...,
        min_length=1,
        description="Hierarchical tags formatted with double-colons (e.g., 'systems::db::concurrency').",
    )
    evaluation: CardEvaluation = Field(
        ...,
        description="Self-evaluative validation audit ensuring card adherence to the atomic retrieval standard.",
    )


class DeckGenerationBatch(BaseModel):
    thought_process: str = Field(
        ...,
        description="High-level reasoning outlining the chunk's scope, themes, and synthesis strategy.",
    )
    extracted_assertions: list[ExtractionStep] = Field(
        ...,
        description="Step-by-step extraction of grounded, atomic assertions before card generation.",
    )
    cards: list[AnkiCard] = Field(
        ...,
        description="Array of validated Anki flashcard objects.",
    )