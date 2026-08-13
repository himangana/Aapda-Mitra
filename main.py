"""Local entry point for the Aapda-Mitra emergency-call backend.

Step 1 deliberately exposes only a health endpoint. It verifies that the
FastAPI service can start without calling Twilio, Deepgram, Groq, Qdrant, or
Rime, preserving free-tier API credits while the integration pipeline is built.
"""

from contextlib import asynccontextmanager
import json
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from twilio.twiml.voice_response import Connect, VoiceResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aapda_mitra")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load local configuration once when the server starts."""
    load_dotenv()
    logger.info("Aapda-Mitra backend started in local development mode")
    yield
    logger.info("Aapda-Mitra backend stopped")


app = FastAPI(
    title="Aapda-Mitra API",
    description="AI-assisted disaster-response call triage service.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Return server status without making an external API request."""
    return {"status": "ok", "service": "aapda-mitra-backend"}


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
