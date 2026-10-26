"""Local audio transcription using faster-whisper."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from faster_whisper import WhisperModel

from src.core.exceptions import IngestionError

logger = logging.getLogger(__name__)


class LocalAudioTranscriber:
    """Transcribes audio files locally using CTranslate2 faster-whisper."""

    def __init__(
        self,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str = "int8",
    ) -> None:
        self.model_size = model_size or os.getenv("WHISPER_MODEL_SIZE", "base")
        self.device = device or os.getenv("WHISPER_DEVICE", "cpu")
        self.compute_type = compute_type
        self._model: WhisperModel | None = None

    @property
    def model(self) -> WhisperModel:
        """Lazy-load the Whisper model only when audio fallback is triggered."""
        if self._model is None:
            logger.info(
                "Loading faster-whisper model '%s' on %s (%s)...",
                self.model_size,
                self.device,
                self.compute_type,
            )
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe_file(self, audio_path: str | Path) -> str:
        """Transcribe an audio file into a cleaned text block."""
        path = Path(audio_path)
        if not path.exists():
            raise IngestionError(f"Audio file not found: {path}")

        try:
            segments, info = self.model.transcribe(
                str(path),
                beam_size=5,
                vad_filter=True,
            )
            logger.info(
                "Detected language '%s' with probability %.2f",
                info.language,
                info.language_probability,
            )
            transcript_parts = [segment.text.strip() for segment in segments]
            return " ".join(transcript_parts)
        except Exception as err:
            raise IngestionError(f"Failed to transcribe audio file {path}: {err}") from err