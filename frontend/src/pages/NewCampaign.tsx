import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError, LapsedContact, Workspace } from "../api/client";

export default function NewCampaign() {
  const { ws } = useParams();
  const wsId = Number(ws);
  const nav = useNavigate();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [lapsed, setLapsed] = useState<LapsedContact[]>([]);
  const [templateName, setTemplateName] = useState("");
  const [discount, setDiscount] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [w, l] = await Promise.all([api.getWorkspace(wsId), api.listLapsed(wsId)]);
        setWorkspace(w);
        setLapsed(l);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load");
      }
    })();
  }, [wsId]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const campaign = await api.createCampaign(wsId, {
        template_name: templateName,
        discount_offer: discount || undefined,
      });
      nav(`/workspaces/${wsId}/campaigns/${campaign.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to send");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Link to={`/workspaces/${wsId}/contacts`} className="muted">← Contacts</Link>
      <h2>New campaign · {workspace?.name}</h2>

      <form className="card" onSubmit={submit}>
        <div className="field">
          <label>AiSensy campaign name</label>
          <input
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            placeholder="e.g. winback_offer_v1"
            required
          />
          <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            Must exactly match a <strong>Live</strong> API campaign in your AiSensy
            dashboard (bound to a Meta-approved template).
          </p>
        </div>
        <div className="field">
          <label>Discount / offer (fills the template's {"{{1}}"} variable)</label>
          <input
            value={discount}
            onChange={(e) => setDiscount(e.target.value)}
            placeholder="e.g. 20% off your next visit"
          />
        </div>

        <div className="card" style={{ background: "#faf9f6" }}>
          <label>Preview</label>
          <p style={{ marginTop: 4 }}>
            Template <strong>{templateName || "…"}</strong>
            {discount && <> with offer “<strong>{discount}</strong>”</>} will be sent to{" "}
            <strong>{lapsed.length}</strong> lapsed contact(s).
          </p>
        </div>

        {error && <div className="error">{error}</div>}
        <button className="primary" disabled={busy || lapsed.length === 0}>
          {busy ? "Sending…" : `Send to ${lapsed.length} lapsed contact${lapsed.length === 1 ? "" : "s"}`}
        </button>
        {lapsed.length === 0 && <p className="muted">No lapsed contacts to send to.</p>}
      </form>
    </>
  );
}
