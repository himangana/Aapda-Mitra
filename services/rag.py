"""NDRF-grounded retrieval with an optional Qdrant Cloud mirror.

The local corpus makes the hackathon demo reliable offline.  When
``QDRANT_REMOTE_ENABLED=true`` the same chunks are mirrored to Qdrant and
queried there; otherwise no remote service or credits are touched.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


NDRF_FLOOD_SOURCE_URL = "https://ndrf.gov.in/sites/default/files/English%20SSP.pdf"
COLLECTION_NAME = "ndrf_flood_guidance"
CORPUS_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "ndrf_flood_guidance.md"


@dataclass(frozen=True)
class GuidanceMatch:
    text: str
    source_title: str
    source_url: str
    retrieval_mode: str


def _chunks() -> list[str]:
    """Read markdown sections as short retrievable guidance chunks."""
    content = CORPUS_PATH.read_text(encoding="utf-8")
    sections = re.split(r"\n## ", content)
    return [section.strip() for section in sections[1:] if section.strip() and "Demo safety" not in section]


def _keywords(value: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", value.casefold()))


def _local_retrieve(query: str) -> GuidanceMatch:
    query_terms = _keywords(query)
    ranked = sorted(
        _chunks(),
        key=lambda chunk: len(query_terms & _keywords(chunk)),
        reverse=True,
    )
    return GuidanceMatch(
        text=ranked[0],
        source_title="NDRF Flood Safety Do's and Don'ts",
        source_url=NDRF_FLOOD_SOURCE_URL,
        retrieval_mode="local_official_corpus",
    )


def _embedding(text: str, dimensions: int = 64) -> list[float]:
    """Stable dependency-free embedding for the Qdrant demo collection.

    It is intentionally simple rather than a semantic-model substitute.  It
    lets a new Railway deployment avoid a multi-hundred-MB model download; a
    production deployment can replace it with a trained embedding provider.
    """
    vector = [0.0] * dimensions
    for term in _keywords(text):
        bucket = int(hashlib.sha256(term.encode()).hexdigest(), 16) % dimensions
        vector[bucket] += 1.0
    magnitude = sum(value * value for value in vector) ** 0.5 or 1.0
    return [value / magnitude for value in vector]


def _qdrant_request(method: str, path: str, body: dict | None = None) -> dict:
    url = os.environ["QDRANT_URL"].rstrip("/") + path
    headers = {"Content-Type": "application/json", "api-key": os.environ["QDRANT_API_KEY"]}
    request = Request(url, data=json.dumps(body).encode() if body else None, headers=headers, method=method)
    with urlopen(request, timeout=8) as response:  # nosec B310: URL is operator-supplied config
        payload = response.read().decode()
    return json.loads(payload) if payload else {}


def sync_qdrant_corpus() -> int:
    """Create/update the small official NDRF collection. Explicit admin action."""
    if not os.getenv("QDRANT_URL") or not os.getenv("QDRANT_API_KEY"):
        raise RuntimeError("QDRANT_URL and QDRANT_API_KEY are required to sync Qdrant")
    try:
        _qdrant_request(
            "PUT",
            f"/collections/{COLLECTION_NAME}",
            {"vectors": {"size": 64, "distance": "Cosine"}},
        )
    except HTTPError as exc:
        # Qdrant returns 409 when the collection already exists.  Upserting
        # the known point IDs below is idempotent, so a sync can be retried.
        if exc.code != 409:
            raise
    points = [
        {"id": index + 1, "vector": _embedding(chunk), "payload": {"text": chunk, "source_url": NDRF_FLOOD_SOURCE_URL}}
        for index, chunk in enumerate(_chunks())
    ]
    _qdrant_request("PUT", f"/collections/{COLLECTION_NAME}/points?wait=true", {"points": points})
    return len(points)


def _remote_retrieve(query: str) -> GuidanceMatch | None:
    try:
        response = _qdrant_request(
            "POST",
            f"/collections/{COLLECTION_NAME}/points/search",
            {"vector": _embedding(query), "limit": 1, "with_payload": True},
        )
        result = response.get("result", [])
        if result and result[0].get("payload", {}).get("text"):
            payload = result[0]["payload"]
            return GuidanceMatch(
                text=payload["text"],
                source_title="NDRF Flood Safety Do's and Don'ts",
                source_url=payload.get("source_url", NDRF_FLOOD_SOURCE_URL),
                retrieval_mode="qdrant",
            )
    except (URLError, TimeoutError, KeyError, ValueError, OSError):
        # The local official corpus is intentional resilience, not a silent
        # invented answer when a cloud dependency is unavailable.
        return None
    return None


def retrieve_guidance(query: str) -> GuidanceMatch:
    """Retrieve the most relevant official flood-safety chunk safely."""
    # A configured deployment uses Qdrant; empty/local configuration still
    # falls back immediately to the bundled official corpus.
    if os.getenv("QDRANT_REMOTE_ENABLED", "true").casefold() == "true":
        remote = _remote_retrieve(query)
        if remote:
            return remote
    return _local_retrieve(query)
