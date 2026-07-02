import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, CampaignRoi } from "../api/client";

export default function CampaignResults() {
  const { ws, cid } = useParams();
  const wsId = Number(ws);
  const cId = Number(cid);
  const [roi, setRoi] = useState<CampaignRoi | null>(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      setRoi(await api.campaignRoi(wsId, cId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load");
    }
  }
  useEffect(() => {
    load();
    // Poll while a send is in flight so the panel fills in live.
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [wsId, cId]);

  async function toggle(mid: number, booked: boolean) {
    try {
      await api.toggleBooked(wsId, cId, mid, booked);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed");
    }
  }

  if (error) return <div className="error">{error}</div>;
  if (!roi) return <p className="muted">Loading…</p>;

  return (
    <>
      <Link to={`/workspaces/${wsId}/contacts`} className="muted">← Contacts</Link>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>Campaign #{roi.campaign.id} · {roi.campaign.template_name}</h2>
        <span className="tag">status: {roi.campaign.status}</span>
      </div>

      <div className="stat-grid" style={{ marginBottom: 20 }}>
        <Stat n={roi.sent} l="Sent" />
        <Stat n={roi.delivered} l="Delivered" />
        <Stat n={roi.read} l="Read" />
        <Stat n={roi.replied} l="Replied" />
        <Stat n={roi.booked} l="Booked" />
        <Stat n={roi.failed} l="Failed" />
        <div className="stat revenue">
          <div className="n">₹{roi.estimated_revenue.toLocaleString("en-IN")}</div>
          <div className="l">Est. revenue</div>
        </div>
      </div>
      <p className="muted" style={{ marginTop: -8 }}>
        Est. revenue = {roi.booked} booked × ₹{roi.avg_ticket} avg ticket. Mark replies as booked below to grow it.
      </p>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Messages</h3>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Contact #</th>
                <th>Status</th>
                <th>WhatsApp id</th>
                <th>Detail</th>
                <th>Booked</th>
              </tr>
            </thead>
            <tbody>
              {roi.messages.map((m) => (
                <tr key={m.id}>
                  <td>{m.contact_id}</td>
                  <td><span className={`badge ${m.status}`}>{m.status}</span></td>
                  <td className="muted" style={{ fontSize: 12 }}>{m.whatsapp_message_id || "—"}</td>
                  <td className="muted" style={{ fontSize: 12, maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {m.error_detail || "—"}
                  </td>
                  <td>
                    <label style={{ display: "flex", gap: 6, textTransform: "none", margin: 0 }}>
                      <input
                        type="checkbox"
                        style={{ width: "auto" }}
                        checked={m.booked}
                        onChange={(e) => toggle(m.id, e.target.checked)}
                      />
                      booked
                    </label>
                  </td>
                </tr>
              ))}
              {roi.messages.length === 0 && (
                <tr><td colSpan={5} className="muted">No messages yet — the send may still be in progress.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function Stat({ n, l }: { n: number; l: string }) {
  return (
    <div className="stat">
      <div className="n">{n}</div>
      <div className="l">{l}</div>
    </div>
  );
}
