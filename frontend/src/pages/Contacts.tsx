import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, Contact, LapsedContact, UploadSummary, Workspace } from "../api/client";

export default function Contacts() {
  const { ws } = useParams();
  const wsId = Number(ws);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [lapsed, setLapsed] = useState<LapsedContact[]>([]);
  const [summary, setSummary] = useState<UploadSummary | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const lapsedIds = new Set(lapsed.map((c) => c.id));

  async function load() {
    try {
      const [w, c, l] = await Promise.all([
        api.getWorkspace(wsId),
        api.listContacts(wsId),
        api.listLapsed(wsId),
      ]);
      setWorkspace(w);
      setContacts(c);
      setLapsed(l);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load");
    }
  }
  useEffect(() => {
    load();
  }, [wsId]);

  async function upload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    setSummary(null);
    try {
      setSummary(await api.uploadContacts(wsId, file));
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <>
      <Link to="/" className="muted">← Workspaces</Link>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>{workspace?.name || "Contacts"}</h2>
        <Link to={`/workspaces/${wsId}/campaigns/new`}>
          <button className="primary">New campaign →</button>
        </Link>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Upload contacts (CSV)</h3>
        <p className="muted" style={{ fontSize: 13 }}>
          Columns: <code>name, phone, last_visit_date</code>. Re-uploading the same phone updates it — no duplicates.
        </p>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <input ref={fileRef} type="file" accept=".csv" style={{ maxWidth: 320 }} />
          <button className="primary" onClick={upload} disabled={busy}>
            {busy ? "Uploading…" : "Upload"}
          </button>
        </div>
        {summary && (
          <p style={{ marginBottom: 0 }}>
            <strong>{summary.created}</strong> created · <strong>{summary.updated}</strong> updated ·{" "}
            <strong>{summary.skipped}</strong> skipped
            {summary.errors.length > 0 && (
              <details style={{ marginTop: 6 }}>
                <summary className="muted">{summary.errors.length} row issue(s)</summary>
                <ul>{summary.errors.map((e, i) => <li key={i} className="muted">{e}</li>)}</ul>
              </details>
            )}
          </p>
        )}
      </div>

      {error && <div className="error">{error}</div>}

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <h3 style={{ marginTop: 0 }}>Contacts ({contacts.length})</h3>
          <span className="tag">{lapsed.length} lapsed (highlighted)</span>
        </div>
        {contacts.length === 0 ? (
          <p className="muted">No contacts yet — upload a CSV above.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Phone</th>
                  <th>Last visit</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {contacts.map((c) => {
                  const isLapsed = lapsedIds.has(c.id);
                  return (
                    <tr key={c.id} className={isLapsed ? "lapsed" : ""}>
                      <td>{c.name || <span className="muted">—</span>}</td>
                      <td>{c.phone}</td>
                      <td>{c.last_visit_date || <span className="muted">never</span>}</td>
                      <td>
                        {isLapsed ? (
                          <span className="badge failed">lapsed</span>
                        ) : (
                          <span className="muted">active</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
