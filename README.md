# Aapda-Mitra

**AI-led voice triage for disaster response — no app, no download, just a phone call.**

Deployment link: https://frontend-phi-seven-12.vercel.app/caller

https://github.com/user-attachments/assets/d5ac111d-e305-481d-b877-5635098b71e1

---

## Problem Statement

In the recent past, we saw devastating floods hit Assam, and deadly fires kill people in Delhi.

People called. The system helped. But we still lost people.

The problem is not just one of victim-to-rescuer ratio — it is of the help being deployed where and when it is needed the most.

---

## Our Solution

Aapda-Mitra is an AI voice agent that answers emergency calls directly over a normal phone line — no app, no smartphone, no login required. It listens to the caller in real time, asks the right follow-up questions, and turns a panicked, unstructured phone call into a structured incident report with a 0–10 urgency score, ready for a human dispatcher to review and approve in seconds.

We never let the AI guess. Every response is grounded in official NDRF rescue manuals, retrieved live and matched against the caller's changing situation — not generated freely by an LLM.

### Why This Works When It Matters Most

This works when it matters most — during a disaster, when everything else is failing.

**First — it doesn't need a smartphone, an app, or even a good internet connection.** Aapda-Mitra runs on a normal phone call. No download, no login, no app store. If a person can dial a number on a basic Nokia keypad, they can reach us. That's the reality of rural India during a flood — the network is jammed, the phone is old, and there's no time to install anything.

**Second — speed and respect for the caller.** The agent starts speaking in under a second of the call connecting. No dead air, no "please hold." And the moment the caller starts talking — even mid-sentence — the agent stops instantly and listens. Because a panicking person doesn't want to argue with a robot. They want to be heard.

**Third — every call ends in something actionable.** Not just a transcript. A structured report: what happened, where it happened, and an urgency score from 0 to 10 — sent straight to a human dispatcher's screen. They see it, they verify it, they click approve. We're not replacing the rescue team's judgment. We're making sure they get the right call, first, in seconds instead of minutes.

---

## Architecture & Tech Stack

To make this system work in real time under disaster conditions, our architecture relies heavily on instant data processing and our sponsor technologies.

- **The Foundation — Pathway (VoxForge track):** our system is built to handle live, uninterrupted data streams instantly.
- **The Memory — Qdrant:** we never let the AI guess. Qdrant instantly fetches official NDRF rescue manuals and tracks the caller's changing context — like water rising from ankles to chest.
- **The Voice — Rime:** a long pause feels like a dropped call, so we integrated Rime. The agent starts speaking in under 100 milliseconds and instantly cuts out the moment the caller talks, ensuring a panicked victim is never talked over.

**Call flow:**

1. **Twilio** connects the caller's phone to our server and streams live audio both ways.
2. **Deepgram** transcribes the live audio to text in real time.
3. **Qdrant** performs content-based (not keyword) retrieval against the NDRF manual knowledge base to ground the response in verified procedure.
4. **Grok** acts as the AI brain, combining the transcribed text and retrieved context to form a response.
5. **Rime** converts the response back to speech fast enough to keep the conversation natural.
6. A persistent **WebSocket connection** keeps the whole pipeline live for the duration of the call.

Hosting: the API layer is split across **Railway** (Twilio, Deepgram, Grok, Rime) and **Vercel** (user-facing output), tied together over the same live WebSocket connection.

<img width="542" height="530" alt="image" src="https://github.com/user-attachments/assets/bccd868b-e79e-4d49-8333-e2757a8db233" />

---

## Current Market & Competition

So — are we the first to think of AI in emergency response? No. And we want to be upfront about that.

112 India already routes calls across ten channels. Telangana's Dial 112 already uses AI to prioritize and route. In the US, Carbyne and RapidSOS already do AI-powered triage. This is a real, moving space.

But look closely at what all of them have in common: the AI assists a human call-taker. It transcribes, it flags, it prioritizes — but a person is still the one talking to the caller. Even Carbyne, the closest thing to us, only lets AI run the non-emergency calls. The moment it's a real crisis, it hands back to a human.

We do the opposite. Aapda-Mitra is the one letting AI run the actual emergency conversation — start to finish — grounded in official rescue manuals so it never guesses, and gated by a human who approves before anyone is dispatched.

That's not a feature difference. That's an architecture difference. And it's the question we expect to be asked next: why trust AI to talk to someone mid-crisis? Our answer — it never talks alone. Every word it says comes from a verified manual, and every action it recommends waits for a human to say yes.

**Competitive advantage: AI-led voice triage with human approval. No incumbent offers both.** Compared against real deployed systems — not generic categories: 112 India / ERSS, Telangana AI-112, and Carbyne / Axon 911.

<img width="1080" height="748" alt="image" src="https://github.com/user-attachments/assets/27f19930-734e-4cfa-9ec4-0c12fa1a8af0" />

**Why now, why this stack:** Government 112 systems and US platforms like Carbyne/RapidSOS use AI to assist a human call-taker, or restrict full automation to non-emergency lines. None let AI run the emergency conversation itself with retrieval-grounded guidance — real-time voice models and fast vector search now make that possible on ordinary phone lines.

---

## Business Plan

Looking at the future of Aapda-Mitra, we see a strong opportunity for growth and large-scale impact.

**Market size:** the Indian incident and emergency management market is projected to grow from around $3.26 billion in 2024 to $6.27 billion by 2029, showing growing demand for smarter and more connected emergency-response solutions.

**Scaling approach:** we start with campuses and local communities, then expand to cities, state-level networks, and eventually larger emergency-response ecosystems. As more users, responders, and organizations join the platform, the system becomes more connected and useful.

**Deployment model:** modular and low-infrastructure — Aapda-Mitra plugs into an existing emergency helpline number rather than replacing the underlying dispatch system, which keeps integration cost and disruption low compared to a full platform overhaul like Carbyne/Axon.

**Revenue model:** licensing/subscription to state disaster management authorities and municipal bodies, priced on call volume and concurrent-line capacity, with an enterprise tier for private/industrial sites (factories, large campuses) that need their own emergency line.

**Roadmap:** going forward, our roadmap includes AI-assisted emergency prioritization, multilingual support, and integration with IoT and existing emergency systems. These additions can make Aapda-Mitra faster, more accessible, and more intelligent.

---

## Getting Started (Local Setup)

Aapda-Mitra has two parts: a FastAPI backend (voice-triage server) and a React/Vite frontend (dispatcher dashboard).

### 1. Clone the repo

```bash
git clone https://github.com/himangana/Aapda-Mitra.git
cd Aapda-Mitra
```

### 2. Backend setup

```bash
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` with your API keys (Twilio, Groq, Qdrant, Deepgram, Rime) as needed. For local testing without incurring paid API calls, the defaults already set `DEEPGRAM_STT_ENABLED=false`, `GROQ_TRIAGE_ENABLED=false`, and `QDRANT_REMOTE_ENABLED=false`, so the app falls back to mock behavior and the local NDRF corpus.

Run the server:

```bash
uvicorn main:app --reload --port 8000
```

### 3. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
```

The default `VITE_API_BASE_URL=http://localhost:8000` already points at your local backend.

```bash
npm run dev
```

The dispatcher dashboard will be available at `http://localhost:5173`.

### 4. (Optional) Live phone calls

Real calls require a public HTTPS tunnel so Twilio can reach your local server, e.g.:

```bash
ngrok http 8000
```

Set the resulting URL as `PUBLIC_BASE_URL` in `.env`.

### 5. Running tests

```bash
# Frontend
cd frontend
npm run test:ui     # Vitest unit tests
npm run test:e2e    # Playwright end-to-end tests

# Backend
pip install pytest
pytest tests/
```

### Notes

- Full functionality (live voice calls, real-time transcription, AI triage, vector search) requires valid API keys for Twilio, Deepgram, Groq, Qdrant, and Rime — none are bundled with this repo.
- `SQLITE_DATABASE_PATH` controls where the local SQLite database file is created; no separate database setup is required.

---

## Conclusion

Our goal isn't just to build another emergency platform. It's to reduce the gap between someone asking for help and the right response reaching them.

Because in an emergency, every second matters. Aapda-Mitra turns those critical seconds into coordinated action — connecting the right help to the right person, when it matters most.

---

##Credit

Rime
Qdrant
Waya
Pathway
