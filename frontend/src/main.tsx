import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./styles.css";
import { getToken } from "./api/client";
import Login from "./pages/Login";
import Workspaces from "./pages/Workspaces";
import Contacts from "./pages/Contacts";
import NewCampaign from "./pages/NewCampaign";
import CampaignResults from "./pages/CampaignResults";
import Layout from "./components/Layout";

function RequireAuth({ children }: { children: React.ReactNode }) {
  return getToken() ? <>{children}</> : <Navigate to="/login" replace />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route path="/" element={<Workspaces />} />
          <Route path="/workspaces/:ws/contacts" element={<Contacts />} />
          <Route path="/workspaces/:ws/campaigns/new" element={<NewCampaign />} />
          <Route path="/workspaces/:ws/campaigns/:cid" element={<CampaignResults />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
