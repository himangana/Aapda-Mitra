"""Safe, deterministic triage fallback for the hackathon prototype.

The rule engine keeps the demo usable when a model or retrieval service is
unavailable. It is deliberately labelled as a fallback: production decisions
must use retrieved NDRF guidance and human dispatcher approval.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriageResult:
    urgency_score: int
    disaster_type: str
    recommended_action: str
    caller_guidance: str


DISASTER_KEYWORDS = {
    "flood": ("flood", "water level", "rising water", "drowning"),
    "fire": ("fire", "smoke", "burning"),
    "earthquake": ("earthquake", "collapsed building", "rubble"),
    "landslide": ("landslide", "mudslide", "hill collapse"),
    "storm": ("cyclone", "storm", "high wind"),
}


def classify_emergency(transcript: str) -> TriageResult:
    """Classify a transcript using conservative emergency-response rules."""
    text = transcript.casefold()
    disaster_type = "other"
    for name, keywords in DISASTER_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            disaster_type = name
            break

    if any(keyword in text for keyword in ("prank", "wrong number", "test call")):
        return TriageResult(0, "invalid", "Log without dispatch", "This call is being logged.")

    critical = (
        "unconscious",
        "not breathing",
        "severe bleeding",
        "trapped",
        "collapsed building",
        "rising water",
        "drowning",
        "fire inside",
    )
    if any(keyword in text for keyword in critical):
        return TriageResult(
            10,
            disaster_type,
            "Immediate emergency dispatch",
            "Stay on the line if safe. Move away from immediate danger only if you can do so safely.",
        )

    high_risk = ("pregnant", "infant", "baby", "elderly", "disabled", "stranded", "rapidly")
    if any(keyword in text for keyword in high_risk):
        return TriageResult(
            8,
            disaster_type,
            "Priority rescue assessment",
            "Stay in the safest available place and keep the phone reachable while help is assessed.",
        )

    moderate = ("no food", "no water", "medicine", "medical supplies", "trapped at home")
    if any(keyword in text for keyword in moderate):
        return TriageResult(
            5,
            disaster_type,
            "Schedule supply or evacuation support",
            "Conserve supplies, remain in a safe location, and await dispatcher follow-up.",
        )

    return TriageResult(
        2,
        disaster_type,
        "Send automated guidance",
        "A dispatcher can provide local shelter and road-status guidance. Call again if danger increases.",
    )
