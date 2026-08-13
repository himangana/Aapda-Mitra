import React, { useEffect, useMemo, useState } from "react";

// Production requests stay on the Vercel origin and are proxied to Railway by
// vercel.json. This avoids browser CORS failures during the live demo.
const API_BASE_URL = "";

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
        <div className="status"><span /> Live triage queue</div>
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

export default App;
