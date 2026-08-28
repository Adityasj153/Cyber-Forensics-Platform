import { z } from "zod";

// Inline copies of the exact Zod schemas from lib/api-client.ts (kept in sync).
const CaseSchema = z.object({
  id: z.string(), name: z.string(), description: z.string().nullable(),
  status: z.string(), created_by: z.string(), created_at: z.string(), updated_at: z.string(),
});
const DeviceSchema = z.object({
  id: z.string(), case_id: z.string(), device_type: z.string(),
  os: z.string().nullable(), owner: z.string().nullable(), name: z.string().nullable(),
});
const ArtifactSchema = z.object({
  id: z.string(), filename: z.string(), sha256: z.string(), status: z.string(),
  status_reason: z.string().nullable(), uploaded_at: z.string(),
});
const LogEventSchema = z.object({
  id: z.string(), timestamp: z.string(), source_type: z.string(),
  actor: z.string().nullable(), action: z.string(), object: z.string().nullable(),
  ip_address: z.string().nullable(), file_hash: z.string().nullable(),
  detail: z.string().nullable(), device_id: z.string().nullable().optional(),
  artifact_id: z.string().nullable().optional(), raw_line: z.string().nullable().optional(),
});
const AnomalySchema = z.object({
  id: z.string(), event_ids: z.array(z.string()), score: z.number(),
  severity: z.string(), category: z.string(), model_name: z.string(),
  model_version: z.string().nullable(), explanation: z.record(z.unknown()).nullable(),
  review_status: z.string(), created_at: z.string(),
});
const CorrelationEdgeSchema = z.object({
  id: z.string(), entity_a_id: z.string(), entity_b_id: z.string(),
  relation_type: z.string(), confidence: z.number(), evidence_event_ids: z.array(z.string()),
  explanation: z.record(z.unknown()).nullable(), model_version: z.string().nullable(),
  created_at: z.string(),
});
const EntitySchema = z.object({
  id: z.string(), entity_type: z.string(), value: z.string(),
  metadata: z.record(z.unknown()).nullable(),
});
const SearchResponseSchema = z.object({ total: z.number(), events: z.array(LogEventSchema) });

const BASE = process.env.API_URL || "http://localhost:8000";
const caseId = process.argv[2];
const token = process.env.API_TOKEN;

if (!caseId || !token) {
  console.error("usage: API_TOKEN=<jwt> node verify-zod-populated.mjs <case_id>");
  process.exit(2);
}

const H = { Authorization: `Bearer ${token}` };

function check(name, schema, data) {
  try {
    schema.parse(data);
    const counts = Array.isArray(data) ? data.length : 1;
    console.log(`PASS ${name}${Array.isArray(data) ? ` (${counts} items)` : ""}`);
    return true;
  } catch (e) {
    console.log(`FAIL ${name}`);
    if (e.issues) {
      e.issues.slice(0, 5).forEach((i) =>
        console.log(`   ${i.path.join(".")}: ${i.message} (got: ${JSON.stringify(i.input)?.slice(0, 60)})`)
      );
    }
    return false;
  }
}

const checks = [
  ["case", CaseSchema, `${BASE}/api/cases/${caseId}`],
  ["devices", z.array(DeviceSchema), `${BASE}/api/cases/${caseId}/devices`],
  ["artifacts", z.array(ArtifactSchema), `${BASE}/api/cases/${caseId}/logs`],
  ["search (populated log events)", SearchResponseSchema, `${BASE}/api/cases/${caseId}/search?size=200`],
  ["anomalies", z.array(AnomalySchema), `${BASE}/api/cases/${caseId}/anomalies`],
  ["correlations", z.array(CorrelationEdgeSchema), `${BASE}/api/cases/${caseId}/correlations`],
  ["entities", z.array(EntitySchema), `${BASE}/api/cases/${caseId}/entities`],
];

let allPass = true;
for (const [name, schema, url] of checks) {
  try {
    const res = await fetch(url, { headers: H });
    if (!res.ok) {
      console.log(`FAIL ${name} (HTTP ${res.status} ${await res.text()})`);
      allPass = false;
      continue;
    }
    const json = await res.json();
    if (!check(name, schema, json)) allPass = false;
  } catch (e) {
    console.log(`FAIL ${name} (fetch error: ${e.message})`);
    allPass = false;
  }
}

console.log(allPass ? "ALL ZOD CHECKS PASSED" : "ZOD CHECKS FAILED");
process.exit(allPass ? 0 : 1);
