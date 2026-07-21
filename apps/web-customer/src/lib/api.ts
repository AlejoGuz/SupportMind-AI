const API_BASE = import.meta.env.VITE_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail?.message || body?.detail || res.statusText);
  }
  return res.json();
}

export type ChatNode = {
  session_id: string;
  public_token: string;
  node_id: string;
  node_code: string;
  prompt: string;
  node_type: string;
  options: { id: string; label: string; sort_order: number }[];
  outcome: string | null;
  blocked_message: string | null;
};

export type Product = {
  id: string;
  sku: string;
  name: string;
  family: string;
  brand: string;
};

export type ActiveIncident = {
  id: string;
  number: string;
  problem_code: string;
  public_message: string;
  title: string;
};

export const api = {
  products: () => request<Product[]>("/api/v1/catalog/products"),
  activeIncidents: () => request<ActiveIncident[]>("/api/v1/public/incidents/active"),
  startSession: (product_id?: string) =>
    request<ChatNode>("/api/v1/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ tree_slug: "phone-power", product_id: product_id ?? null }),
    }),
  answer: (sessionId: string, option_id: string) =>
    request<ChatNode>(`/api/v1/chat/sessions/${sessionId}/answers`, {
      method: "POST",
      body: JSON.stringify({ option_id }),
    }),
  escalate: (sessionId: string, payload: Record<string, unknown>) =>
    request(`/api/v1/chat/sessions/${sessionId}/escalate`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
