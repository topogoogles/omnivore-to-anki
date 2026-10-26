"""Custom domain exceptions for Omnivore-to-Anki."""


class OmnivoreError(Exception):
    """Base exception for all Omnivore-to-Anki errors."""


class IngestionError(OmnivoreError):
    """Raised when a document, audio file, or URL fails to load or transcribe."""


class ValidationError(OmnivoreError):
    """Raised when generated flashcards fail quality or schema checks."""


class SyncError(OmnivoreError):
    """Raised when communicating with AnkiConnect fails."""