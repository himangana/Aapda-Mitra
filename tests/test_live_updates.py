"""Unit tests for the low-cost dispatcher queue update broker."""

import asyncio
import unittest

from services.live_updates import ReportUpdateBroker


class ReportUpdateBrokerTests(unittest.IsolatedAsyncioTestCase):
    async def test_broadcasts_a_refresh_invalidation_to_each_subscriber(self) -> None:
        broker = ReportUpdateBroker()
        first = broker.subscribe()
        second = broker.subscribe()
        first_next = asyncio.create_task(anext(first))
        second_next = asyncio.create_task(anext(second))
        await asyncio.sleep(0)

        created = await broker.publish("report_created", "report-123")

        self.assertEqual(created.sequence, 1)
        self.assertEqual((await first_next).as_dict(), created.as_dict())
        self.assertEqual((await second_next).as_dict(), created.as_dict())
        await first.aclose()
        await second.aclose()

    async def test_a_slow_subscriber_keeps_the_newest_invalidation(self) -> None:
        broker = ReportUpdateBroker(queue_size=1)
        subscriber = broker.subscribe()
        waiting = asyncio.create_task(anext(subscriber))
        await asyncio.sleep(0)

        await broker.publish("report_created", "older")
        self.assertEqual((await waiting).report_id, "older")
        await broker.publish("report_created", "stale")
        newest = await broker.publish("report_approved", "newest")

        self.assertEqual((await anext(subscriber)).as_dict(), newest.as_dict())
        await subscriber.aclose()
