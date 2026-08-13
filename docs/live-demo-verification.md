# Live caller-to-dispatcher demo verification

## Current deployment audit (2026-08-13)

The deployed Railway queue endpoint returns `200` with `Cache-Control:
no-store, max-age=0`. The public command-center Playwright journeys passed in
Chromium: critical-report creation/approval and the mobile guidance flow.

The backend's existing `GET /api/reports` endpoint is therefore sufficient for
a reliable hackathon live-update mechanism. Use short polling as the primary
mechanism: it works across Railway restarts, multiple browser tabs, and a
missed request always self-heals at the next poll.

## Recommended caller-demo interaction

1. Caller page submits the final transcript to `POST /api/triage`.
2. Caller page immediately shows the returned guidance.
3. Command center polls `GET /api/reports` every 3 seconds while the page is
   visible, and stops polling when the tab is hidden.
4. Command center refreshes immediately after its own create/approve actions.

No additional API key, WebSocket, or cross-origin browser permission is needed
for this path. The frontend must keep using its same-origin `/api` proxy.

## Optional SSE enhancement

`services/live_updates.py` provides a dependency-free in-process invalidation
broker for a later Server-Sent Events route. It publishes only an event name,
report ID, and sequence number; the browser must still reload `/api/reports`,
which keeps SQLite authoritative.

Before exposing SSE, wire the broker into report creation and approval, then
test the route with a single Railway replica. Do not treat the in-memory broker
as durable or cross-replica messaging.

## Browser acceptance test

Run two browser contexts against the public Vercel alias:

1. Open `/caller` in one context and `/` in another.
2. Submit a uniquely identifiable critical recording/transcript from `/caller`.
3. Assert the command center shows that report without a manual refresh within
   5 seconds, with the correct urgency and pending-review count.
4. Approve it in the command center and verify the caller receives the approved
   state/guidance according to the selected demo UX.
5. Repeat with microphone denied and confirm typed transcript fallback works.
6. Throttle/offline the caller request and confirm a clear retry message; no
   duplicate report must be created on one retry.
