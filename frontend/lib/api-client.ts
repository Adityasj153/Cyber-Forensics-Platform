const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
}

export interface Case {
  id: string;
  name: string;
  description: string | null;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Device {
  id: string;
  case_id: string;
  device_type: string;
  os: string | null;
  owner: string | null;
  name: string | null;
}

export interface Artifact {
  id: string;
  filename: string;
  sha256: string;
  status: string;
  status_reason: string | null;
  uploaded_at: string;
}

export interface LogEvent {
  id: string;
  timestamp: string;
  source_type: string;
  actor: string | null;
  action: string;
  object: string | null;
  ip_address: string | null;
  file_hash: string | null;
  detail: string | null;
  device_id?: string | null;
  artifact_id?: string | null;
  raw_line?: string | null;
}

export interface Anomaly {
  id: string;
  event_ids: string[];
  score: number;
  severity: string;
  category: string;
  model_name: string;
  model_version: string | null;
  explanation: Record<string, unknown> | null;
  review_status: string;
  created_at: string;
}

export interface CorrelationEdge {
  id: string;
  entity_a_id: string;
  entity_b_id: string;
  relation_type: string;
  confidence: number;
  evidence_event_ids: string[];
  explanation: Record<string, unknown> | null;
  model_version: string | null;
  created_at: string;
}

export interface Entity {
  id: string;
  entity_type: string;
  value: string;
  metadata: Record<string, unknown> | null;
}

export interface SearchResponse {
  total: number;
  events: LogEvent[];
}

// ── API Client ─────────────────────────────────────────────────────────────

export const api = {
  auth: {
    login: (username: string, password: string) =>
      request<{ access_token: string }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }),
    register: (data: { username: string; email: string; password: string; role?: string }) =>
      request<User>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    me: () => request<User>("/api/auth/me"),
  },

  cases: {
    list: () => request<Case[]>("/api/cases"),
    get: (id: string) => request<Case>(`/api/cases/${id}`),
    create: (data: { name: string; description?: string }) =>
      request<Case>("/api/cases", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<{ name: string; description: string; status: string }>) =>
      request<Case>(`/api/cases/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },

  devices: {
    list: (caseId: string) => request<Device[]>(`/api/cases/${caseId}/devices`),
    create: (caseId: string, data: { device_type: string; os?: string; owner?: string; name?: string }) =>
      request<Device>(`/api/cases/${caseId}/devices`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  artifacts: {
    list: (caseId: string) => request<Artifact[]>(`/api/cases/${caseId}/logs`),
    upload: async (caseId: string, file: File, deviceId?: string) => {
      const formData = new FormData();
      formData.append("file", file);
      if (deviceId) {
        formData.append("device_id", deviceId);
      }
      const token = getToken();
      const res = await fetch(`${API_BASE}/api/cases/${caseId}/logs`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(error.detail || `HTTP ${res.status}`);
      }
      return res.json() as Promise<Artifact>;
    },
  },

  search: {
    query: (caseId: string, params: {
      query?: string;
      source_type?: string;
      action?: string;
      device_id?: string;
      ip_address?: string;
      timestamp_from?: string;
      timestamp_to?: string;
      offset?: number;
      size?: number;
    }) => {
      const sp = new URLSearchParams();
      if (params.query) sp.set("query", params.query);
      if (params.source_type) sp.set("source_type", params.source_type);
      if (params.action) sp.set("action", params.action);
      if (params.device_id) sp.set("device_id", params.device_id);
      if (params.ip_address) sp.set("ip_address", params.ip_address);
      if (params.timestamp_from) sp.set("timestamp_from", params.timestamp_from);
      if (params.timestamp_to) sp.set("timestamp_to", params.timestamp_to);
      sp.set("offset", String(params.offset ?? 0));
      sp.set("size", String(params.size ?? 50));
      return request<SearchResponse>(`/api/cases/${caseId}/search?${sp.toString()}`);
    },
  },

  anomalies: {
    list: (caseId: string, params?: { severity?: string; category?: string }) => {
      const sp = new URLSearchParams();
      if (params?.severity) sp.set("severity", params.severity);
      if (params?.category) sp.set("category", params.category);
      const qs = sp.toString();
      return request<Anomaly[]>(`/api/cases/${caseId}/anomalies${qs ? `?${qs}` : ""}`);
    },
    review: (caseId: string, anomalyId: string, reviewStatus: "confirmed" | "dismissed") =>
      request<{ status: string; reviewed_by: string }>(
        `/api/cases/${caseId}/anomalies/${anomalyId}/review`,
        {
          method: "PATCH",
          body: JSON.stringify({ review_status: reviewStatus }),
        }
      ),
  },

  correlations: {
    list: (caseId: string, params?: { relation_type?: string; min_confidence?: number }) => {
      const sp = new URLSearchParams();
      if (params?.relation_type) sp.set("relation_type", params.relation_type);
      if (params?.min_confidence !== undefined) sp.set("min_confidence", String(params.min_confidence));
      const qs = sp.toString();
      return request<CorrelationEdge[]>(`/api/cases/${caseId}/correlations${qs ? `?${qs}` : ""}`);
    },
  },

  entities: {
    list: (caseId: string, params?: { entity_type?: string }) => {
      const sp = new URLSearchParams();
      if (params?.entity_type) sp.set("entity_type", params.entity_type);
      const qs = sp.toString();
      return request<Entity[]>(`/api/cases/${caseId}/entities${qs ? `?${qs}` : ""}`);
    },
  },
};
