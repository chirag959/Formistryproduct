// Thin fetch wrapper. Token is kept in localStorage; every call is prefixed
// with the API base (proxied to /api in dev, VITE_API_BASE in prod).

const API_BASE = (import.meta.env.VITE_API_BASE as string) || "/api";
const TOKEN_KEY = "formistry_token";
const USER_KEY = "formistry_user";

export interface User {
  id: number;
  email: string;
  role: "admin" | "staff";
  workspace_id: number | null;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as User) : null;
}

export function setSession(token: string, user: User) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearSession();
    window.location.href = "/login";
    throw new ApiError(401, "Session expired");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  listWorkspaces: () => request<Workspace[]>("/workspaces"),
  createWorkspace: (body: Partial<Workspace>) =>
    request<Workspace>("/workspaces", { method: "POST", body: JSON.stringify(body) }),
  getWorkspace: (id: number) => request<Workspace>(`/workspaces/${id}`),

  listContacts: (ws: number) => request<Contact[]>(`/workspaces/${ws}/contacts`),
  listLapsed: (ws: number) => request<LapsedContact[]>(`/workspaces/${ws}/contacts/lapsed`),
  uploadContacts: (ws: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<UploadSummary>(`/workspaces/${ws}/contacts/upload`, {
      method: "POST",
      body: fd,
    });
  },

  listCampaigns: (ws: number) => request<Campaign[]>(`/workspaces/${ws}/campaigns`),
  createCampaign: (ws: number, body: { template_name: string; discount_offer?: string }) =>
    request<Campaign>(`/workspaces/${ws}/campaigns`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  campaignRoi: (ws: number, cid: number) =>
    request<CampaignRoi>(`/workspaces/${ws}/campaigns/${cid}`),
  toggleBooked: (ws: number, cid: number, mid: number, booked: boolean) =>
    request<Message>(
      `/workspaces/${ws}/campaigns/${cid}/messages/${mid}/booked?booked=${booked}`,
      { method: "POST" }
    ),
};

// --- Types mirrored from backend schemas ---
export interface Workspace {
  id: number;
  name: string;
  whatsapp_phone_number_id: string | null;
  lapsed_threshold_days: number;
  avg_ticket: number;
  created_at: string;
}
export interface Contact {
  id: number;
  name: string | null;
  phone: string;
  last_visit_date: string | null;
  created_at: string;
}
export interface LapsedContact extends Contact {
  days_since_visit: number | null;
}
export interface UploadSummary {
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
}
export interface Campaign {
  id: number;
  template_name: string;
  discount_offer: string | null;
  status: string;
  created_at: string;
}
export interface Message {
  id: number;
  contact_id: number;
  status: string;
  whatsapp_message_id: string | null;
  error_detail: string | null;
  booked: boolean;
  sent_at: string | null;
}
export interface CampaignRoi {
  campaign: Campaign;
  sent: number;
  delivered: number;
  read: number;
  replied: number;
  failed: number;
  booked: number;
  avg_ticket: number;
  estimated_revenue: number;
  messages: Message[];
}
