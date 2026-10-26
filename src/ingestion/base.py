"""Abstract base class for all source ingestors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSourceLoader(ABC):
    """Standard interface for extracting raw text and metadata from any source."""

    @abstractmethod
    def ingest(self, source: str, **kwargs: Any) -> dict[str, Any]:
        """Extract raw text and metadata from the given source path or URL."""
        raise NotImplementedError