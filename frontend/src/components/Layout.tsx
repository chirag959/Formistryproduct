import { Link, Outlet, useNavigate } from "react-router-dom";
import { clearSession, getUser } from "../api/client";

export default function Layout() {
  const nav = useNavigate();
  const user = getUser();
  return (
    <>
      <div className="topbar">
        <Link to="/" style={{ textDecoration: "none", color: "inherit" }}>
          <span className="brand">FORMISTRY · REBOOKING</span>
        </Link>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <span className="muted">{user?.email}</span>
          <span className="tag">{user?.workspace_id ? "workspace" : "agency admin"}</span>
          <button
            className="link-btn"
            onClick={() => {
              clearSession();
              nav("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </div>
      <div className="container">
        <Outlet />
      </div>
    </>
  );
}
