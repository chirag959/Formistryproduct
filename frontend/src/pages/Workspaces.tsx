import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, getUser, Workspace } from "../api/client";

export default function Workspaces() {
  const user = getUser();
  const isAgency = user && user.workspace_id === null && user.role === "admin";
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [error, setError] = useState("");
  const [showNew, setShowNew] = useState(false);

  async function load() {
    try {
      setWorkspaces(await api.listWorkspaces());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load");
    }
  }
  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>Workspaces</h2>
        {isAgency && (
          <button className="primary" onClick={() => setShowNew((s) => !s)}>
            {showNew ? "Cancel" : "+ New workspace"}
          </button>
        )}
      </div>
      {error && <div className="error">{error}</div>}
      {showNew && <NewWorkspace onCreated={() => { setShowNew(false); load(); }} />}

      {workspaces.length === 0 && !error && <p className="muted">No workspaces yet.</p>}
      <div className="row">
        {workspaces.map((w) => (
          <div className="card" key={w.id} style={{ minWidth: 260 }}>
            <h3 style={{ marginTop: 0 }}>{w.name}</h3>
            <p className="muted" style={{ fontSize: 13 }}>
              Lapsed after {w.lapsed_threshold_days} days · Avg ticket ₹{w.avg_ticket}
            </p>
            <p style={{ fontSize: 12 }}>
              AiSensy:{" "}
              {w.aisensy_configured ? (
                <span className="badge replied">connected</span>
              ) : (
                <span className="badge failed">not set</span>
              )}
            </p>
            <Link to={`/workspaces/${w.id}/contacts`}>
              <button className="primary" style={{ marginTop: 6 }}>Open →</button>
            </Link>
          </div>
        ))}
      </div>
    </>
  );
}

function NewWorkspace({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [phoneId, setPhoneId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [threshold, setThreshold] = useState(45);
  const [avgTicket, setAvgTicket] = useState(0);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.createWorkspace({
        name,
        whatsapp_phone_number_id: phoneId || null,
        aisensy_api_key: apiKey || null,
        lapsed_threshold_days: Number(threshold),
        avg_ticket: Number(avgTicket),
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed");
    }
  }

  return (
    <form className="card" onSubmit={submit}>
      <h3 style={{ marginTop: 0 }}>New workspace</h3>
      <div className="row">
        <div className="field">
          <label>Business name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="field">
          <label>WhatsApp phone number id (optional)</label>
          <input value={phoneId} onChange={(e) => setPhoneId(e.target.value)} placeholder="from Meta" />
        </div>
      </div>
      <div className="field">
        <label>AiSensy API key</label>
        <input
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          type="password"
          placeholder="from AiSensy dashboard → Manage → API Key (leave blank to use the global key)"
        />
      </div>
      <div className="row">
        <div className="field">
          <label>Lapsed threshold (days)</label>
          <input type="number" value={threshold} onChange={(e) => setThreshold(+e.target.value)} />
        </div>
        <div className="field">
          <label>Avg ticket (₹)</label>
          <input type="number" value={avgTicket} onChange={(e) => setAvgTicket(+e.target.value)} />
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <button className="primary">Create workspace</button>
    </form>
  );
}
