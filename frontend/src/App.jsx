import React, { useEffect, useMemo, useState } from "react";

// Production requests stay on the Vercel origin and are proxied to Railway by
// vercel.json. This avoids browser CORS failures during the live demo.
const API_BASE_URL = "";

function ProductNav({ active }) {
  return (
    <nav className="product-nav" aria-label="Demo views">
      <a className={active === "caller" ? "active" : ""} href="/caller">Caller demo</a>
      <a className={active === "dispatcher" ? "active" : ""} href="/">Dispatcher command center</a>
    </nav>
  );
}

function CallerDemo() {
  const [location, setLocation] = useState("");
  const [transcript, setTranscript] = useState("");
  const [recording, setRecording] = useState(false);
  const [recordedAudio, setRecordedAudio] = useState(null);
  const [recordingUrl, setRecordingUrl] = useState("");
  const [status, setStatus] = useState("Ready to listen");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [report, setReport] = useState(null);
  const recorderRef = React.useRef(null);
  const chunksRef = React.useRef([]);
  const demoTranscript = "We are trapped on the roof. Flood water is rising and my grandmother cannot walk.";

  useEffect(() => () => {
    if (recordingUrl) URL.revokeObjectURL(recordingUrl);
  }, [recordingUrl]);

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError("Recording is not supported in this browser. Type the emergency message below instead.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const audio = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        setRecordedAudio(audio);
        setRecordingUrl(URL.createObjectURL(audio));
        setStatus("Voice message captured — transcribe it or edit the transcript below.");
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
      setError("");
      setStatus("Recording emergency message…");
    } catch {
      setError("Microphone access was not granted. Type the emergency message below instead.");
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    setRecording(false);
  }

  async function transcribeRecording() {
    if (!recordedAudio) return;
    setSubmitting(true);
    setStatus("Transcribing voice message…");
    setError("");
    try {
      const formData = new FormData();
      formData.append("audio", recordedAudio, "emergency-message.webm");
      const response = await fetch(`${API_BASE_URL}/api/transcribe`, { method: "POST", body: formData });
      if (!response.ok) throw new Error("Voice transcription is temporarily unavailable.");
      const result = await response.json();
      if (!result.transcript?.trim()) throw new Error("We could not detect speech in that recording.");
      setTranscript(result.transcript);
      setStatus("Transcript ready — confirm it, then send the request.");
    } catch (requestError) {
      setError(`${requestError.message} You can still type or paste the caller's words for the demo.`);
      setStatus("Use the transcript fallback to continue.");
    } finally {
      setSubmitting(false);
    }
  }

  function useDemoVoiceScenario() {
    setTranscript(demoTranscript);
    setLocation("Dibrugarh, Assam");
    setStatus("Demo voice scenario loaded — send it to the command center.");
    setError("");
  }

  async function submitEmergency(event) {
    event.preventDefault();
    if (transcript.trim().length < 2) {
      setError("Record and transcribe a message, or enter the caller's words first.");
      return;
    }
    setSubmitting(true);
    setStatus("Sending securely to the emergency command center…");
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/triage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript, location: location || null }),
      });
      if (!response.ok) throw new Error("Your emergency request could not be sent. Please try again.");
      const triageReport = await response.json();
      setReport(triageReport);
      setStatus("Request sent. A human dispatcher is reviewing it now.");
      if ("speechSynthesis" in window && triageReport.caller_guidance) {
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(triageReport.caller_guidance));
      }
    } catch (requestError) {
      setError(requestError.message);
      setStatus("Unable to send request.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="caller-shell">
      <header className="caller-header">
        <a className="caller-brand" href="/"><span>◈</span> Aapda-Mitra</a>
        <ProductNav active="caller" />
      </header>
      <section className="caller-hero">
        <p className="eyebrow">EMERGENCY ASSISTANCE DEMO</p>
        <h1>Tell us what is happening.</h1>
        <p>Your voice message is transcribed and sent to a human-supervised disaster-response team.</p>
      </section>
      <form className="caller-card" onSubmit={submitEmergency}>
        <div className="listen-orb" aria-hidden="true"><span className={recording ? "pulse" : ""}>⌁</span></div>
        <h2>{recording ? "Listening…" : "Send an emergency message"}</h2>
        <p className="caller-status" aria-live="polite">{status}</p>
        <div className="record-controls">
          <button className={`record-button ${recording ? "recording" : ""}`} type="button" onClick={recording ? stopRecording : startRecording}>
            <span>{recording ? "■" : "●"}</span> {recording ? "Stop recording" : "Record message"}
          </button>
          {recordedAudio && <button className="secondary-button" type="button" disabled={submitting} onClick={transcribeRecording}>Transcribe recording</button>}
        </div>
        {recordingUrl && <audio className="recording-preview" controls src={recordingUrl}>Your browser cannot play this recording.</audio>}
        <div className="caller-divider"><span>or use the safe text fallback</span></div>
        <button className="demo-voice-button" type="button" onClick={useDemoVoiceScenario}>Use demo emergency scenario</button>
        <label htmlFor="caller-transcript">What happened?</label>
        <textarea id="caller-transcript" value={transcript} onChange={(event) => setTranscript(event.target.value)} rows="5" placeholder="Example: We are trapped on the second floor. Flood water is rising outside." />
        <label htmlFor="caller-location">Where are you? <em>(optional, but helpful)</em></label>
        <input id="caller-location" value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Area, landmark, village, or address" />
        <button className="send-emergency" disabled={submitting}>{submitting ? "Sending…" : "Send to command center"}</button>
        {error && <p className="error" role="alert">{error}</p>}
      </form>
      {report && <section className="guidance-card" aria-live="polite">
        <p className="eyebrow">REQUEST RECEIVED · HUMAN REVIEW REQUIRED</p>
        <h2>{report.urgency_score >= 7 ? "Help is being prioritized" : "Guidance is ready"}</h2>
        <p>{report.caller_guidance}</p>
        <div><b>Assessment:</b> {report.disaster_type} · urgency {report.urgency_score}/10</div>
        <a href="/">Open dispatcher command center →</a>
      </section>}
      <p className="caller-disclaimer">For this prototype, always contact local emergency services in a real emergency.</p>
    </main>
  );
}

const samples = [
  {
    label: "Flood rescue",
    transcript: "We are trapped in rising flood water with my elderly mother.",
    location: "Sector 12, Delhi",
  },
  {
    label: "Shelter guidance",
    transcript: "Our home is safe but we need the nearest shelter and road status.",
    location: "Guwahati, Assam",
  },
];

function urgencyLabel(score) {
  if (score === 10) return "Critical";
  if (score >= 7) return "High risk";
  if (score >= 4) return "Moderate";
  if (score >= 1) return "Information";
  return "Invalid";
}

function App() {
  const [reports, setReports] = useState([]);
  const [transcript, setTranscript] = useState("");
  const [location, setLocation] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const pendingCount = useMemo(
    () => reports.filter((report) => report.dispatcher_status === "pending_human_approval").length,
    [reports],
  );

  async function loadReports() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/reports`, { cache: "no-store" });
      if (!response.ok) throw new Error("Unable to reach the triage service.");
      setReports(await response.json());
      setError("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReports();
    // Browser caller demos and dispatcher screens can be opened side by side.
    // Poll while this tab is foreground so new requests show up without a
    // manual refresh, while keeping the prototype's backend simple.
    const refreshTimer = window.setInterval(() => {
      if (document.visibilityState === "visible") loadReports();
    }, 3000);
    return () => window.clearInterval(refreshTimer);
  }, []);

  async function submitTriage(event) {
    event.preventDefault();
    if (transcript.trim().length < 2) {
      setError("Enter a caller transcript before creating a report.");
      return;
    }
    setSubmitting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/triage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript, location: location || null }),
      });
      if (!response.ok) throw new Error("The rescue report could not be created.");
      const report = await response.json();
      setReports((current) => [report, ...current]);
      setTranscript("");
      setLocation("");
      setError("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function approveReport(reportId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/reports/${reportId}/approve`, { method: "POST" });
      if (!response.ok) throw new Error("Approval could not be recorded.");
      await response.json();
      // Reload the persisted queue so this dispatcher also sees changes made
      // by any other operator during a live incident.
      await loadReports();
      setError("");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function useSample(sample) {
    setTranscript(sample.transcript);
    setLocation(sample.location);
  }

  return (
    <main>
      <header className="topbar">
        <div>
          <p className="eyebrow">DISASTER RESPONSE COMMAND CENTER</p>
          <h1>Aapda-Mitra</h1>
        </div>
        <div className="topbar-actions"><ProductNav active="dispatcher" /><div className="status"><span /> Live triage queue</div></div>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">AI-ASSISTED, HUMAN-APPROVED</p>
          <h2>Every emergency call, prioritized in seconds.</h2>
          <p className="lede">Create a rescue report from a caller transcript, review its urgency, and require a human approval before dispatch.</p>
        </div>
        <aside className="metric">
          <strong>{pendingCount}</strong>
          <span>reports awaiting human approval</span>
        </aside>
      </section>

      <section className="grid">
        <form className="panel form-panel" onSubmit={submitTriage}>
          <div className="panel-heading"><h3>New emergency report</h3><span>Demo input</span></div>
          <label htmlFor="transcript">Caller transcript</label>
          <textarea id="transcript" value={transcript} onChange={(event) => setTranscript(event.target.value)} placeholder="Describe what the caller said…" rows="6" />
          <label htmlFor="location">Location (if known)</label>
          <input id="location" value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Area, landmark, or address" />
          <div className="samples">
            {samples.map((sample) => <button type="button" className="sample" key={sample.label} onClick={() => useSample(sample)}>{sample.label}</button>)}
          </div>
          <button className="primary" disabled={submitting}>{submitting ? "Creating report…" : "Create rescue report"}</button>
          {error && <p className="error" role="alert">{error}</p>}
        </form>

        <section className="panel map-panel">
          <div className="panel-heading"><h3>Response area</h3><a href="https://www.openstreetmap.org" target="_blank" rel="noreferrer">OpenStreetMap ↗</a></div>
          <iframe title="OpenStreetMap India overview" src="https://www.openstreetmap.org/export/embed.html?bbox=68.0%2C7.0%2C97.5%2C37.5&amp;layer=mapnik" />
          <p>Use the caller’s confirmed location to coordinate the appropriate rescue team.</p>
        </section>
      </section>

      <section className="queue">
        <div className="queue-heading"><div><p className="eyebrow">HUMAN DISPATCHER REVIEW</p><h2>Rescue queue</h2></div><button className="refresh" onClick={loadReports}>Refresh</button></div>
        {loading ? <p className="empty">Loading reports…</p> : reports.length === 0 ? <p className="empty">No reports yet. Use the form above to run the demo.</p> : <div className="report-list">
          {reports.map((report) => <article className="report" key={report.id}>
            <div className={`score score-${report.urgency_score}`}><strong>{report.urgency_score}</strong><span>{urgencyLabel(report.urgency_score)}</span></div>
            <div className="report-body"><div className="report-meta"><span>{report.disaster_type}</span><span>{report.location || "Location pending"}</span><span>{new Date(report.created_at).toLocaleString()}</span></div><h3>{report.summary}</h3><p><b>Recommended:</b> {report.recommended_action}</p><p className="guidance">{report.caller_guidance}</p><small>{report.source_status}</small></div>
            <div className="approval">{report.dispatcher_status === "approved_by_human" ? <span className="approved">Approved</span> : <button className="approve" onClick={() => approveReport(report.id)}>Approve dispatch</button>}</div>
          </article>)}
        </div>}
      </section>
    </main>
  );
}

function RoutedApp() {
  return window.location.pathname.replace(/\/$/, "") === "/caller" ? <CallerDemo /> : <App />;
}

export default RoutedApp;
