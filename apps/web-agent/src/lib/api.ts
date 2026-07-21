const API_BASE = import.meta.env.VITE_API_URL ?? "";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("sm_access_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...authHeaders(),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : body?.detail?.message || body?.title || res.statusText,
    );
  }
  return res.json();
}

export type Ticket = {
  id: string;
  number: string;
  status: string;
  priority: string;
  category: string;
  sentiment: string;
  summary_ai: string;
  customer_first_name: string;
  customer_last_name: string;
  customer_email: string;
  product_id: string;
  description: string;
  created_by: string;
  assignee_id: string | null;
  incident_id: string | null;
  conversation_transcript: { prompt: string; answer: string | null; node_code: string }[];
  events: { event_type: string; message: string; actor: string; created_at: string }[];
  attachments: { filename: string; storage_key: string }[];
  created_at: string;
  sla_remaining_seconds: number | null;
};

export type Alert = {
  id: string;
  fingerprint: string;
  problem_code: string;
  ticket_count: number;
  window_seconds: number;
  status: string;
  public_title: string;
  created_at: string;
};

export type Incident = {
  id: string;
  number: string;
  title: string;
  problem_code: string;
  status: string;
  public_message: string;
  ticket_ids: string[];
  created_at: string;
};

export type Metrics = {
  open_tickets: number;
  new_tickets: number;
  pending_alerts: number;
  active_incidents: number;
  resolved_today: number;
  avg_priority_p1: number;
  tickets_by_priority: Record<string, number>;
  tickets_by_status: Record<string, number>;
};

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; refresh_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<{ full_name: string; email: string; roles: string[] }>("/api/v1/agents/me"),
  tickets: () => request<Ticket[]>("/api/v1/tickets"),
  ticket: (id: string) => request<Ticket>(`/api/v1/tickets/${id}`),
  transition: (id: string, status: string) =>
    request(`/api/v1/tickets/${id}/transitions`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
  comment: (id: string, message: string) =>
    request(`/api/v1/tickets/${id}/comments`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  alerts: () => request<Alert[]>("/api/v1/alerts"),
  acceptAlert: (id: string) =>
    request<Incident>(`/api/v1/alerts/${id}/accept`, { method: "POST" }),
  rejectAlert: (id: string, reason: string) =>
    request(`/api/v1/alerts/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  incidents: () => request<Incident[]>("/api/v1/incidents"),
  resolveIncident: (id: string) =>
    request(`/api/v1/incidents/${id}/resolve`, { method: "POST" }),
  metrics: () => request<Metrics>("/api/v1/metrics/overview"),
  agents: () =>
    request<{ id: string; full_name: string; email: string; roles: string[]; availability: string }[]>(
      "/api/v1/agents",
    ),
  audit: () =>
    request<{ id: string; action: string; actor: string; resource_type: string; resource_id: string; created_at: string; details: Record<string, unknown> }[]>(
      "/api/v1/audit",
    ),
  trees: () => request<{ id: string; slug: string; name: string; version: number; is_active: boolean }[]>("/api/v1/admin/decision-trees"),
  sla: () => request<{ priority: string; response_minutes: number; resolution_minutes: number }[]>("/api/v1/admin/sla-policies"),
};
