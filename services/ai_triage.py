"""Strictly validated Groq triage adapter; deterministic rules remain fallback."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.request import Request, urlopen

from services.triage import TriageResult, classify_emergency


@dataclass(frozen=True)
class StructuredTriage:
    result: TriageResult
    summary: str
    mode: str


def triage_with_guidance(transcript: str, guidance: str) -> StructuredTriage:
    """Use Groq only when opted in, otherwise return safe deterministic triage."""
    fallback = classify_emergency(transcript)
    if os.getenv("GROQ_TRIAGE_ENABLED", "false").casefold() != "true":
        return StructuredTriage(fallback, transcript.strip()[:280], "deterministic_fallback")
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return StructuredTriage(fallback, transcript.strip()[:280], "deterministic_fallback")
    prompt = {
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Return JSON only with urgency_score (integer 0-10), disaster_type, summary, recommended_action, caller_guidance. Use only the provided NDRF guidance for safety advice. Never claim dispatch occurred; a human must approve."},
            {"role": "user", "content": f"CALLER TRANSCRIPT:\n{transcript}\n\nNDRF GUIDANCE:\n{guidance}"},
        ],
    }
    try:
        request = Request("https://api.groq.com/openai/v1/chat/completions", data=json.dumps(prompt).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=20) as response:  # nosec B310: fixed provider URL
            payload = json.loads(response.read().decode())
        content = json.loads(payload["choices"][0]["message"]["content"])
        score = int(content["urgency_score"])
        if not 0 <= score <= 10:
            raise ValueError("urgency_score outside safe range")
        result = TriageResult(score, str(content["disaster_type"])[:64], str(content["recommended_action"])[:240], str(content["caller_guidance"])[:600])
        return StructuredTriage(result, str(content["summary"])[:280], "groq_grounded")
    except (KeyError, ValueError, TypeError, OSError, json.JSONDecodeError):
        return StructuredTriage(fallback, transcript.strip()[:280], "deterministic_fallback")
