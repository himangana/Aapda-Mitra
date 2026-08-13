"""Local entry point for the Aapda-Mitra emergency-call backend.

Step 1 deliberately exposes only a health endpoint. It verifies that the
FastAPI service can start without calling Twilio, Deepgram, Groq, Qdrant, or
Rime, preserving free-tier API credits while the integration pipeline is built.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
import json
import logging
import os
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from services.database import (
    approve_report as approve_stored_report,
    create_report,
    initialize_database,
    list_reports as list_stored_reports,
)
from services.triage import classify_emergency
from twilio.twiml.voice_response import Connect, VoiceResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aapda_mitra")
load_dotenv()
database_path = os.getenv("SQLITE_DATABASE_PATH", "aapda_mitra.db")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load local configuration once when the server starts."""
    initialize_database(database_path)
    logger.info("Aapda-Mitra backend started in local development mode")
    yield
    logger.info("Aapda-Mitra backend stopped")


app = FastAPI(
    title="Aapda-Mitra API",
    description="AI-assisted disaster-response call triage service.",
    version="0.1.0",
    lifespan=lifespan,
)

# The dashboard has no login in this hackathon prototype, so it sends no
# cookies. Restrict this list to the deployed Vercel URL after deployment.
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class TriageRequest(BaseModel):
    """A caller transcript supplied by the voice pipeline or demo dashboard."""

    transcript: str = Field(min_length=2, max_length=2_000)
    location: str | None = Field(default=None, max_length=240)


class RescueReport(BaseModel):
    """Human-reviewable result. No AI result can dispatch a rescue directly."""

    id: str
    created_at: datetime
    transcript: str
    location: str | None
    disaster_type: str
    urgency_score: int = Field(ge=0, le=10)
    summary: str
    recommended_action: str
    caller_guidance: str
    source_status: str
    dispatcher_status: str


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Return server status without making an external API request."""
    return {"status": "ok", "service": "aapda-mitra-backend"}


@app.post("/api/triage", response_model=RescueReport, status_code=201, tags=["triage"])
async def triage_call(request: TriageRequest) -> RescueReport:
    """Create a human-reviewable rescue report without dispatching anyone.

    Step 3 will replace the deterministic fallback with NDRF-grounded RAG and
    structured LLM output. The human approval gate remains mandatory.
    """
    result = classify_emergency(request.transcript)
    report = RescueReport(
        id=str(uuid4()),
        created_at=datetime.now(UTC),
        transcript=request.transcript.strip(),
        location=request.location.strip() if request.location else None,
        disaster_type=result.disaster_type,
        urgency_score=result.urgency_score,
        summary=request.transcript.strip()[:280],
        recommended_action=result.recommended_action,
        caller_guidance=result.caller_guidance,
        source_status="Demo safety fallback; NDRF knowledge-base retrieval pending.",
        dispatcher_status="pending_human_approval",
    )
    create_report(
        database_path,
        {
            "id": report.id,
            "created_at": report.created_at.isoformat(),
            "transcript": report.transcript,
            "location": report.location,
            "disaster_type": report.disaster_type,
            "urgency_score": report.urgency_score,
            "summary": report.summary,
            "recommended_action": report.recommended_action,
            "caller_guidance": report.caller_guidance,
            "source_status": report.source_status,
            "dispatcher_status": report.dispatcher_status,
        },
    )
    logger.info("Created triage report %s with urgency %d", report.id, report.urgency_score)
    return report


@app.get("/api/reports", response_model=list[RescueReport], tags=["dispatcher"])
async def list_reports() -> list[RescueReport]:
    """Return the persisted queue for the prototype dispatcher dashboard."""
    return [RescueReport.model_validate(report) for report in list_stored_reports(database_path)]


@app.post("/api/reports/{report_id}/approve", response_model=RescueReport, tags=["dispatcher"])
async def approve_report(report_id: str) -> RescueReport:
    """Record a human dispatcher's approval; this does not contact responders."""
    report = approve_stored_report(database_path, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Rescue report not found")
    logger.info("Dispatcher approved triage report %s", report_id)
    return RescueReport.model_validate(report)


def media_stream_url(request: Request) -> str:
    """Build Twilio's secure WebSocket URL without hard-coding a tunnel URL.

    Set PUBLIC_BASE_URL to the HTTPS ngrok URL for local call testing. In a
    deployed environment, the request's public base URL is used as a fallback.
    """
    public_base_url = os.getenv("PUBLIC_BASE_URL", str(request.base_url)).rstrip("/")
    if public_base_url.startswith("https://"):
        return f"wss://{public_base_url.removeprefix('https://')}/twilio/media-stream"
    if public_base_url.startswith("http://"):
        return f"ws://{public_base_url.removeprefix('http://')}/twilio/media-stream"
    raise ValueError("PUBLIC_BASE_URL must start with http:// or https://")


@app.post("/twilio/voice", tags=["twilio"])
async def answer_incoming_call(request: Request) -> Response:
    """Answer Twilio's inbound webhook and connect the call to our WebSocket.

    This endpoint only creates TwiML; it does not place calls or consume speech,
    LLM, vector-search, or text-to-speech API credits.
    """
    try:
        response = VoiceResponse()
        connect = Connect()
        connect.stream(url=media_stream_url(request))
        response.append(connect)
        return Response(content=str(response), media_type="application/xml")
    except ValueError as exc:
        logger.error("Twilio voice webhook configuration error: %s", exc)
        return Response(
            content="<Response><Say>Service configuration is unavailable.</Say></Response>",
            media_type="application/xml",
            status_code=500,
        )


@app.websocket("/twilio/media-stream")
async def twilio_media_stream(websocket: WebSocket) -> None:
    """Receive Twilio Media Stream events for a single emergency call.

    Twilio sends JSON messages such as `connected`, `start`, `media`, and
    `stop`. Audio is intentionally not forwarded yet: Step 3 will pass each
    validated media chunk to a speech-to-text provider.
    """
    await websocket.accept()
    stream_sid: str | None = None
    media_chunk_count = 0

    try:
        while True:
            payload = json.loads(await websocket.receive_text())
            event = payload.get("event")

            if event == "connected":
                logger.info("Twilio Media Stream connected")
            elif event == "start":
                stream_sid = payload.get("start", {}).get("streamSid")
                logger.info("Twilio Media Stream started: %s", stream_sid or "unknown")
            elif event == "media":
                audio_payload = payload.get("media", {}).get("payload")
                if not isinstance(audio_payload, str) or not audio_payload:
                    logger.warning("Discarded Twilio media event without audio payload")
                    continue
                media_chunk_count += 1
                # Step 3 will stream this base64-encoded mu-law audio to Deepgram.
            elif event == "stop":
                logger.info(
                    "Twilio Media Stream stopped: %s (%d media chunks)",
                    stream_sid or "unknown",
                    media_chunk_count,
                )
                break
            else:
                logger.warning("Ignored unsupported Twilio Media Stream event: %r", event)
    except WebSocketDisconnect:
        logger.info("Twilio Media Stream disconnected: %s", stream_sid or "unknown")
    except json.JSONDecodeError:
        logger.warning("Twilio Media Stream sent invalid JSON")
        await websocket.close(code=1003, reason="Expected a JSON event")
    except Exception:
        logger.exception("Unexpected Twilio Media Stream failure")
        await websocket.close(code=1011, reason="Temporary server error")


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Avoid exposing internal errors to callers while recording diagnostics."""
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."},
    )
