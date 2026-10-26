"""LangGraph self-correcting evaluation graph for AutoAnki configured for Perplexity API."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from src.agents.state import AgentState, QualityIssue
from src.core.schemas import AnkiCard, CardType, DeckGenerationBatch
from src.export.anki_package import AnkiPackageExporter
from src.mcp.tools.anki_connect import AnkiConnectClient

load_dotenv()

logger = logging.getLogger(__name__)

# Pre-load system prompt at module initialization to avoid blocking I/O inside async nodes
SYSTEM_PROMPT_PATH = Path("config/prompts/system_prompt.txt")
BASE_SYSTEM_PROMPT = (
    SYSTEM_PROMPT_PATH.read_text(encoding="utf-8") if SYSTEM_PROMPT_PATH.exists() else ""
)


# ---------------------------------------------------------------------------
# Perplexity LLM & Pydantic Parser Setup
# ---------------------------------------------------------------------------
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar-pro")

parser = PydanticOutputParser(pydantic_object=DeckGenerationBatch)


def parse_perplexity_output(ai_message: AIMessage) -> DeckGenerationBatch:
    """Strip optional <think> blocks or markdown fences from Perplexity output and validate against Pydantic."""
    text = ai_message.content if isinstance(ai_message.content, str) else str(ai_message.content)

    # Remove <think>...</think> blocks if using sonar-reasoning models
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Extract JSON object if wrapped in ```json ... ``` fences or extra commentary
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        text = match.group(0)

    return DeckGenerationBatch.model_validate_json(text)


# Base Perplexity clients using the OpenAI-compatible endpoint
_extract_client = ChatOpenAI(
    model=PERPLEXITY_MODEL,
    api_key=PERPLEXITY_API_KEY,
    base_url="https://api.perplexity.ai",
    temperature=0.1,
)

_refine_client = ChatOpenAI(
    model=PERPLEXITY_MODEL,
    api_key=PERPLEXITY_API_KEY,
    base_url="https://api.perplexity.ai",
    temperature=0.2,
)

# Runnable chains piping LLM output directly into the custom Pydantic sanitizer
structured_llm = _extract_client | parse_perplexity_output
refine_llm = _refine_client | parse_perplexity_output


# ---------------------------------------------------------------------------
# Node 1: Ingestion & Concept Extraction
# ---------------------------------------------------------------------------
async def extract_node(state: AgentState) -> dict[str, Any]:
    """Extract atomic assertions and draft the initial batch of Anki cards using Perplexity."""
    full_system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n{parser.get_format_instructions()}"

    messages = [
        SystemMessage(content=full_system_prompt),
        HumanMessage(
            content=(
                f"Extract core atomic assertions and draft flashcards for the following text:\n\n"
                f"{state['raw_text']}"
            )
        ),
    ]

    response: DeckGenerationBatch = await structured_llm.ainvoke(messages)

    return {
        "thought_process": response.thought_process,
        "extracted_assertions": response.extracted_assertions,
        "draft_cards": response.cards,
        "iteration_count": 0,
        "rejected_issues": [],
    }


# ---------------------------------------------------------------------------
# Node 2: Evaluator / Quality Gate
# ---------------------------------------------------------------------------
async def evaluator_node(state: AgentState) -> dict[str, Any]:
    """Audit cards for atomicity, answer leakage, cloze formatting, and ambiguity."""
    draft_cards = state.get("draft_cards", [])
    accepted_cards: list[AnkiCard] = []
    issues: list[QualityIssue] = []

    conjunction_flags = [" and ", " as well as ", " together with ", " additionally "]

    for card in draft_cards:
        card_has_problem = False

        # 1. Self-reported schema flag checks
        if not card.evaluation.is_atomic:
            issues.append(
                QualityIssue(
                    card_id=card.card_id,
                    issue_type="atomicity_violation",
                    feedback="Card was flagged non-atomic in self-evaluation.",
                    suggested_fix="Split into separate discrete retrieval items.",
                )
            )
            card_has_problem = True

        if card.evaluation.has_leakage:
            issues.append(
                QualityIssue(
                    card_id=card.card_id,
                    issue_type="answer_leakage",
                    feedback="The prompt contains vocabulary cues that expose the target answer.",
                    suggested_fix="Rephrase front prompt to remove giveaway keywords.",
                )
            )
            card_has_problem = True

        # 2. Heuristic check: compound questions violating Minimum Information Principle
        front_lower = card.front.lower()
        if (
            card.card_type == CardType.BASIC
            and any(conj in front_lower for conj in conjunction_flags)
            and "?" in card.front
            and (len(card.back.split(".")) > 2 or ";" in card.back)
        ):
            issues.append(
                QualityIssue(
                    card_id=card.card_id,
                    issue_type="atomicity_violation",
                    feedback=f"Prompt '{card.front}' tests multiple assertions simultaneously.",
                    suggested_fix="Decompose into 2 independent single-assertion questions.",
                )
            )
            card_has_problem = True

        # 3. Cloze validation
        if card.card_type == CardType.CLOZE and "{{c1::" not in card.front:
            issues.append(
                QualityIssue(
                    card_id=card.card_id,
                    issue_type="syntax_error",
                    feedback="Cloze card missing standard {{c1::...}} deletion marker.",
                    suggested_fix="Enclose the key technical term within '{{c1::term}}'.",
                )
            )
            card_has_problem = True

        if not card_has_problem:
            accepted_cards.append(card)

    return {
        "final_cards": accepted_cards,
        "rejected_issues": issues,
    }


# ---------------------------------------------------------------------------
# Router: Determine Next Branch
# ---------------------------------------------------------------------------
def router_condition(state: AgentState) -> Literal["refine_node", "export_node"]:
    """Route back for refinement if errors exist and retries are available."""
    issues = state.get("rejected_issues", [])
    iteration = state.get("iteration_count", 0)
    max_retries = state.get("max_retries", 2)

    if issues and iteration < max_retries:
        logger.warning(
            "Validation found %d issues on iteration %d. Routing to refine_node.",
            len(issues),
            iteration,
        )
        return "refine_node"

    logger.info("Validation passed or max retries reached. Routing to export_node.")
    return "export_node"


# ---------------------------------------------------------------------------
# Node 3: Refiner (Self-Correction Loop)
# ---------------------------------------------------------------------------
async def refine_node(state: AgentState) -> dict[str, Any]:
    """Re-prompt Perplexity specifically focused on correcting the failed cards."""
    iteration = state.get("iteration_count", 0) + 1
    issues = state.get("rejected_issues", [])
    accepted = state.get("final_cards", [])

    critique_lines = [
        f"- Card ID: {i['card_id']} | Type: {i['issue_type']} | Critique: {i['feedback']} | Action: {i['suggested_fix']}"
        for i in issues
    ]
    critique_text = "\n".join(critique_lines)

    refine_system_prompt = (
        "You are AutoAnki-Core repairing sub-optimal flashcards. Rewrite low-yield or compound "
        "Anki cards into strict atomic cards.\n\n"
        f"{parser.get_format_instructions()}"
    )

    refine_user_prompt = (
        f"The following cards failed our quality gate:\n\n"
        f"{critique_text}\n\n"
        f"Original Source Context:\n{state['raw_text']}\n\n"
        f"Regenerate ONLY replacement cards that fix all listed violations. Ensure strict atomicity and zero leakage."
    )

    response: DeckGenerationBatch = await refine_llm.ainvoke(
        [
            SystemMessage(content=refine_system_prompt),
            HumanMessage(content=refine_user_prompt),
        ]
    )

    combined_drafts = accepted + response.cards

    return {
        "draft_cards": combined_drafts,
        "iteration_count": iteration,
        "rejected_issues": [],
    }


# ---------------------------------------------------------------------------
# Node 4: Export Node
# ---------------------------------------------------------------------------
async def export_node(state: AgentState) -> dict[str, Any]:
    """Sync cards to AnkiConnect or compile an offline .apkg file."""
    cards_to_export = state.get("final_cards", [])
    deck_name = state.get("deck_name", "Omnivore::AutoGenerated")

    if not cards_to_export:
        return {"export_summary": {"status": "empty", "added": 0, "offline_fallback": False}}

    anki_client = AnkiConnectClient()
    can_connect = await anki_client.ping()

    if can_connect:
        sync_result = await anki_client.sync_cards(cards_to_export, deck_name=deck_name)
        return {
            "export_summary": {
                "status": "synced_via_ankiconnect",
                "added": sync_result["added"],
                "skipped": sync_result["skipped"],
                "errors": sync_result["errors"],
            }
        }

    exporter = AnkiPackageExporter(deck_name=deck_name)
    output_path = f"data/cache/{deck_name.replace('::', '_').lower()}.apkg"
    saved_path = exporter.export_to_file(cards_to_export, output_path)

    return {
        "export_summary": {
            "status": "exported_offline_apkg",
            "file_path": str(saved_path),
            "card_count": len(cards_to_export),
        }
    }


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------
def build_autoanki_graph():
    """Build and compile the self-correcting evaluation LangGraph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("extract_node", extract_node)
    workflow.add_node("evaluator_node", evaluator_node)
    workflow.add_node("refine_node", refine_node)
    workflow.add_node("export_node", export_node)

    workflow.add_edge(START, "extract_node")
    workflow.add_edge("extract_node", "evaluator_node")

    workflow.add_conditional_edges(
        "evaluator_node",
        router_condition,
        {
            "refine_node": "refine_node",
            "export_node": "export_node",
        },
    )

    workflow.add_edge("refine_node", "evaluator_node")
    workflow.add_edge("export_node", END)

    return workflow.compile()


autoanki_graph = build_autoanki_graph()