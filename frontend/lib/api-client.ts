import { getSession } from "next-auth/react";
import { z } from "zod";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  const session = await getSession();
  return (session as any)?.accessToken ?? null;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  schema?: z.ZodType<T>,
): Promise<T> {
  const token = await getToken();
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

  const json = await res.json();
  if (schema) {
    return schema.parse(json);
  }
  return json as T;
}

// ── Zod Schemas ─────────────────────────────────────────────────────────────

export const UserSchema = z.object({
  id: z.string(),
  username: z.string(),
  email: z.string(),
  role: z.string(),
});

export const CaseSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  status: z.string(),
  created_by: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const DeviceSchema = z.object({
  id: z.string(),
  case_id: z.string(),
  device_type: z.string(),
  os: z.string().nullable(),
  owner: z.string().nullable(),
  name: z.string().nullable(),
});

export const ArtifactSchema = z.object({
  id: z.string(),
  filename: z.string(),
  sha256: z.string(),
  status: z.string(),
  status_reason: z.string().nullable(),
  uploaded_at: z.string(),
});

export const LogEventSchema = z.object({
  id: z.string(),
  timestamp: z.string(),
  source_type: z.string(),
  actor: z.string().nullable(),
  action: z.string(),
  object: z.string().nullable(),
  ip_address: z.string().nullable(),
  file_hash: z.string().nullable(),
  detail: z.string().nullable(),
  device_id: z.string().nullable().optional(),
  artifact_id: z.string().nullable().optional(),
  raw_line: z.string().nullable().optional(),
});

export const AnomalySchema = z.object({
  id: z.string(),
  event_ids: z.array(z.string()),
  score: z.number(),
  severity: z.string(),
  category: z.string(),
  model_name: z.string(),
  model_version: z.string().nullable(),
  explanation: z.record(z.unknown()).nullable(),
  review_status: z.string(),
  created_at: z.string(),
});

export const CorrelationEdgeSchema = z.object({
  id: z.string(),
  entity_a_id: z.string(),
  entity_b_id: z.string(),
  relation_type: z.string(),
  confidence: z.number(),
  evidence_event_ids: z.array(z.string()),
  explanation: z.record(z.unknown()).nullable(),
  model_version: z.string().nullable(),
  created_at: z.string(),
});

export const EntitySchema = z.object({
  id: z.string(),
  entity_type: z.string(),
  value: z.string(),
  metadata: z.record(z.unknown()).nullable(),
});

export const SearchResponseSchema = z.object({
  total: z.number(),
  events: z.array(LogEventSchema),
});

// ── Inferred Types ──────────────────────────────────────────────────────────

export type User = z.infer<typeof UserSchema>;
export type Case = z.infer<typeof CaseSchema>;
export type Device = z.infer<typeof DeviceSchema>;
export type Artifact = z.infer<typeof ArtifactSchema>;
export type LogEvent = z.infer<typeof LogEventSchema>;
export type Anomaly = z.infer<typeof AnomalySchema>;
export type CorrelationEdge = z.infer<typeof CorrelationEdgeSchema>;
export type Entity = z.infer<typeof EntitySchema>;
export type SearchResponse = z.infer<typeof SearchResponseSchema>;

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
      }, UserSchema),
    me: () => request<User>("/api/auth/me", {}, UserSchema),
  },

  cases: {
    list: () => request<Case[]>("/api/cases", {}, z.array(CaseSchema)),
    get: (id: string) => request<Case>(`/api/cases/${id}`, {}, CaseSchema),
    create: (data: { name: string; description?: string }) =>
      request<Case>("/api/cases", {
        method: "POST",
        body: JSON.stringify(data),
      }, CaseSchema),
    update: (id: string, data: Partial<{ name: string; description: string; status: string }>) =>
      request<Case>(`/api/cases/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }, CaseSchema),
  },

  devices: {
    list: (caseId: string) => request<Device[]>(`/api/cases/${caseId}/devices`, {}, z.array(DeviceSchema)),
    create: (caseId: string, data: { device_type: string; os?: string; owner?: string; name?: string }) =>
      request<Device>(`/api/cases/${caseId}/devices`, {
        method: "POST",
        body: JSON.stringify(data),
      }, DeviceSchema),
  },

  artifacts: {
    list: (caseId: string) => request<Artifact[]>(`/api/cases/${caseId}/logs`, {}, z.array(ArtifactSchema)),
    upload: async (caseId: string, file: File, deviceId?: string) => {
      const formData = new FormData();
      formData.append("file", file);
      if (deviceId) {
        formData.append("device_id", deviceId);
      }
      const token = await getToken();
      const res = await fetch(`${API_BASE}/api/cases/${caseId}/logs`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(error.detail || `HTTP ${res.status}`);
      }
      const json = await res.json();
      return ArtifactSchema.parse(json);
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
      return request<SearchResponse>(`/api/cases/${caseId}/search?${sp.toString()}`, {}, SearchResponseSchema);
    },
  },

  anomalies: {
    list: (caseId: string, params?: { severity?: string; category?: string }) => {
      const sp = new URLSearchParams();
      if (params?.severity) sp.set("severity", params.severity);
      if (params?.category) sp.set("category", params.category);
      const qs = sp.toString();
      return request<Anomaly[]>(`/api/cases/${caseId}/anomalies${qs ? `?${qs}` : ""}`, {}, z.array(AnomalySchema));
    },
    review: (caseId: string, anomalyId: string, reviewStatus: "confirmed" | "dismissed") =>
      request<{ status: string; reviewed_by: string }>(
        `/api/cases/${caseId}/anomalies/${anomalyId}/review`,
        {
          method: "PATCH",
          body: JSON.stringify({ review_status: reviewStatus }),
        },
        z.object({ status: z.string(), reviewed_by: z.string() }),
      ),
  },

  correlations: {
    list: (caseId: string, params?: { relation_type?: string; min_confidence?: number }) => {
      const sp = new URLSearchParams();
      if (params?.relation_type) sp.set("relation_type", params.relation_type);
      if (params?.min_confidence !== undefined) sp.set("min_confidence", String(params.min_confidence));
      const qs = sp.toString();
      return request<CorrelationEdge[]>(`/api/cases/${caseId}/correlations${qs ? `?${qs}` : ""}`, {}, z.array(CorrelationEdgeSchema));
    },
  },

  entities: {
    list: (caseId: string, params?: { entity_type?: string }) => {
      const sp = new URLSearchParams();
      if (params?.entity_type) sp.set("entity_type", params.entity_type);
      const qs = sp.toString();
      return request<Entity[]>(`/api/cases/${caseId}/entities${qs ? `?${qs}` : ""}`, {}, z.array(EntitySchema));
    },
  },
};
