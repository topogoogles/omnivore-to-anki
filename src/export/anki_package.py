"""Standalone .apkg file generator using genanki."""

from __future__ import annotations

import hashlib
from pathlib import Path

import genanki

from src.core.schemas import AnkiCard, CardType

BASIC_MODEL_ID = 1607392319
CLOZE_MODEL_ID = 1607392320

BASIC_STYLE = """
.card {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 19px;
    text-align: left;
    color: #1a1a1a;
    background-color: #ffffff;
    line-height: 1.5;
    padding: 16px;
}
.extra {
    margin-top: 14px;
    padding-top: 10px;
    border-top: 1px dashed #d1d5db;
    font-size: 15px;
    color: #4b5563;
}
"""

CLOZE_STYLE = BASIC_STYLE + """
.cloze {
    font-weight: bold;
    color: #2563eb;
}
"""

BASIC_MODEL = genanki.Model(
    BASIC_MODEL_ID,
    "Omnivore Basic Model",
    fields=[
        {"name": "Front"},
        {"name": "Back"},
        {"name": "ExtraContext"},
    ],
    templates=[
        {
            "name": "Card 1",
            "qfmt": "{{Front}}",
            "afmt": '{{Front}}<hr id="answer">{{Back}}'
            '{{#ExtraContext}}<div class="extra">{{ExtraContext}}</div>{{/ExtraContext}}',
        },
    ],
    css=BASIC_STYLE,
)

CLOZE_MODEL = genanki.Model(
    CLOZE_MODEL_ID,
    "Omnivore Cloze Model",
    model_type=genanki.Model.CLOZE,
    fields=[
        {"name": "Text"},
        {"name": "BackExtra"},
    ],
    templates=[
        {
            "name": "Cloze Card",
            "qfmt": "{{cloze:Text}}",
            "afmt": '{{cloze:Text}}<hr id="answer">{{#BackExtra}}<div class="extra">{{BackExtra}}</div>{{/BackExtra}}',
        },
    ],
    css=CLOZE_STYLE,
)


def _generate_deck_id(deck_name: str) -> int:
    """Generate a consistent 31-bit positive integer ID from the deck name."""
    digest = hashlib.sha256(deck_name.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) & 0x7FFFFFFF


class AnkiPackageExporter:
    """Compiles lists of AnkiCard objects into standalone .apkg archive files."""

    def __init__(self, deck_name: str = "Omnivore::SpacedRepetition") -> None:
        self.deck_name = deck_name
        self.deck_id = _generate_deck_id(deck_name)

    def _build_note(self, card: AnkiCard) -> genanki.Note:
        """Convert an internal AnkiCard to a genanki Note with deterministic GUID."""
        guid = genanki.guid_for(card.card_id, card.front)

        if card.card_type == CardType.CLOZE:
            return genanki.Note(
                model=CLOZE_MODEL,
                fields=[card.front, card.extra_context or card.back],
                tags=card.tags,
                guid=guid,
            )

        return genanki.Note(
            model=BASIC_MODEL,
            fields=[card.front, card.back, card.extra_context or ""],
            tags=card.tags,
            guid=guid,
        )

    def export_to_file(self, cards: list[AnkiCard], output_path: str | Path) -> Path:
        """Write all cards into a ready-to-import .apkg file on disk."""
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        deck = genanki.Deck(self.deck_id, self.deck_name)
        for card in cards:
            note = self._build_note(card)
            deck.add_note(note)

        package = genanki.Package(deck)
        package.write_to_file(str(target_path))
        return target_path