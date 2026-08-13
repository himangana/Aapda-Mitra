"""In-process event feed for keeping a prototype dispatcher queue live.

The SQLite queue remains the source of truth.  This broker only tells
connected clients that they should refresh that queue, so a missed event never
causes an emergency report to disappear.  It is deliberately dependency-free
and is appropriate for one Railway process, which is the deployment topology
for this hackathon demo.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QueueUpdate:
    """A small invalidation event; clients reload ``GET /api/reports``."""

    event: str
    report_id: str
    sequence: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "report_id": self.report_id,
            "sequence": self.sequence,
        }


class ReportUpdateBroker:
    """Broadcast queue changes to a bounded set of in-process subscribers."""

    def __init__(self, *, queue_size: int = 8) -> None:
        self._queue_size = queue_size
        self._sequence = 0
        self._subscribers: set[asyncio.Queue[QueueUpdate]] = set()

    async def publish(self, event: str, report_id: str) -> QueueUpdate:
        """Publish an invalidation without allowing a slow client to block calls."""
        self._sequence += 1
        update = QueueUpdate(event=event, report_id=report_id, sequence=self._sequence)
        for subscriber in tuple(self._subscribers):
            if subscriber.full():
                # An invalidation is not a durable event. Dropping an old one is
                # safe because every following event still instructs a refresh.
                subscriber.get_nowait()
            subscriber.put_nowait(update)
        return update

    async def subscribe(self) -> AsyncIterator[QueueUpdate]:
        """Yield updates until the caller closes the subscription."""
        subscriber: asyncio.Queue[QueueUpdate] = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers.add(subscriber)
        try:
            while True:
                yield await subscriber.get()
        finally:
            self._subscribers.discard(subscriber)
