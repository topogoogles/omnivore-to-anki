"""YouTube transcript extractor with automatic yt-dlp + faster-whisper fallback."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yt_dlp
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

from src.core.exceptions import IngestionError
from src.ingestion.audio import LocalAudioTranscriber
from src.ingestion.base import BaseSourceLoader

logger = logging.getLogger(__name__)


class YouTubeIngestor(BaseSourceLoader):
    """Extracts transcripts from YouTube URLs via Captions API or Local Whisper fallback."""

    def __init__(
        self,
        cache_dir: str = "data/cache",
        preferred_languages: list[str] | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.preferred_languages = preferred_languages or ["en", "es"]
        self.transcriber = LocalAudioTranscriber()

    @staticmethod
    def extract_video_id(url: str) -> str:
        """Extract the 11-character YouTube video ID from standard or shortened URLs."""
        patterns = [
            r"(?:youtube\.com\/watch\?.*v=)([0-9A-Za-z_-]{11})(?:[&#?]|$)",
            r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})(?:[&#?\/]|$)",
            r"(?:youtube\.com\/(?:embed|v|shorts|live)\/)([0-9A-Za-z_-]{11})(?:[&#?\/]|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise IngestionError(f"Could not parse a valid YouTube video ID from URL: {url}")

    def _fetch_captions(self, video_id: str) -> str | None:
        """Attempt fast caption extraction via youtube-transcript-api."""
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            try:
                transcript = transcript_list.find_manually_created_transcript(
                    self.preferred_languages
                )
            except NoTranscriptFound:
                transcript = transcript_list.find_generated_transcript(
                    self.preferred_languages
                )

            entries = transcript.fetch()
            text = " ".join(
                entry["text"].replace("\n", " ").strip() for entry in entries
            )
            logger.info("Successfully extracted captions for video ID %s", video_id)
            return text

        except (TranscriptsDisabled, NoTranscriptFound) as err:
            logger.warning(
                "Captions unavailable for video %s (%s). Falling back to audio download + Whisper.",
                video_id,
                err.__class__.__name__,
            )
            return None
        except (OSError, ValueError, KeyError, RuntimeError) as err:
            logger.warning("Unexpected error fetching captions for %s: %s", video_id, err)
            return None

    def _download_audio(self, url: str, video_id: str) -> Path:
        """Download low-bitrate m4a/mp3 audio stream using yt-dlp."""
        output_template = str(self.cache_dir / f"{video_id}.%(ext)s")
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = Path(ydl.prepare_filename(info))
                if not downloaded_file.exists():
                    raise IngestionError("yt-dlp finished but output audio file was not found.")
                return downloaded_file
        except (OSError, ValueError, KeyError, RuntimeError) as err:
            raise IngestionError(f"Failed to download audio via yt-dlp for {url}: {err}") from err

    def ingest(self, source: str, cleanup_audio: bool = True, **kwargs: Any) -> dict[str, Any]:
        """Fetch transcript and metadata from a YouTube URL."""
        video_id = self.extract_video_id(source)

        transcript_text = self._fetch_captions(video_id)
        method_used = "youtube_captions_api"

        if not transcript_text:
            method_used = "faster_whisper_local"
            audio_path = self._download_audio(source, video_id)
            try:
                transcript_text = self.transcriber.transcribe_file(audio_path)
            finally:
                if cleanup_audio and audio_path.exists():
                    audio_path.unlink()

        return {
            "video_id": video_id,
            "source_url": source,
            "ingestion_method": method_used,
            "raw_text": transcript_text,
        }