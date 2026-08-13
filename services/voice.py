"""Speech-to-text adapter with an explicit, credit-safe local fallback."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Transcription:
    transcript: str
    provider: str


def transcribe_audio(audio: bytes, content_type: str) -> Transcription:
    """Transcribe browser-recorded audio using Deepgram when deliberately enabled.

    Set ``DEEPGRAM_STT_ENABLED=true`` only for controlled integration testing.
    A configured ``DEEPGRAM_MOCK_TRANSCRIPT`` gives demos a deterministic
    fallback without sending caller audio to a third party.
    """
    mock = os.getenv("DEEPGRAM_MOCK_TRANSCRIPT", "").strip()
    if os.getenv("DEEPGRAM_STT_ENABLED", "false").casefold() != "true":
        if mock:
            return Transcription(mock, "mock")
        raise RuntimeError("Speech-to-text is not enabled; provide a transcript or enable Deepgram")
    api_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPGRAM_API_KEY is not configured")
    request = Request(
        "https://api.deepgram.com/v1/listen?model=nova-3&smart_format=true&detect_language=true",
        data=audio,
        headers={"Authorization": f"Token {api_key}", "Content-Type": content_type or "audio/webm"},
        method="POST",
    )
    with urlopen(request, timeout=25) as response:  # nosec B310: fixed provider URL
        payload = json.loads(response.read().decode())
    transcript = payload["results"]["channels"][0]["alternatives"][0]["transcript"].strip()
    if not transcript:
        raise RuntimeError("Deepgram returned an empty transcript")
    return Transcription(transcript, "deepgram")
