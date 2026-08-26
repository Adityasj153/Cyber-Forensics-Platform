"use client";

import { useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import { api, Device, Anomaly } from "@/lib/api-client";
import Timeline from "@/components/timeline";

const MOCK_CASE_ID = "__mock__";

const MOCK_EVENTS = [
  {
    id: "evt-001",
    timestamp: "2026-08-26T09:14:00Z",
    source_type: "windows_evtx",
    actor: "jsmith",
    action: "file_transfer",
    object: "Q3_financials.xlsx → USB",
    ip_address: null,
    file_hash: "a1b2c3d4e5f6",
    detail: "File copied to removable storage",
    device_id: "PC-04771",
  },
  {
    id: "evt-002",
    timestamp: "2026-08-26T09:15:30Z",
    source_type: "windows_evtx",
    actor: "jsmith",
    action: "logon",
    object: null,
    ip_address: "192.168.1.45",
    file_hash: null,
    detail: "Interactive logon",
    device_id: "PC-04771",
  },
  {
    id: "evt-003",
    timestamp: "2026-08-26T09:17:00Z",
    source_type: "android_logcat",
    actor: "system",
    action: "file_write",
    object: "Q3_financials.xlsx",
    ip_address: null,
    file_hash: "a1b2c3d4e5f6",
    detail: "Same file hash appears on mobile device",
    device_id: "MOBILE-2291",
  },
  {
    id: "evt-004",
    timestamp: "2026-08-26T09:19:00Z",
    source_type: "android_logcat",
    actor: "jsmith",
    action: "email_sent",
    object: "Q3_financials.xlsx → external",
    ip_address: "203.0.113.42",
    file_hash: "a1b2c3d4e5f6",
    detail: "File attached to email sent to external IP",
    device_id: "MOBILE-2291",
  },
  {
    id: "evt-005",
    timestamp: "2026-08-26T09:22:00Z",
    source_type: "network_generic",
    actor: null,
    action: "network_connection",
    object: "203.0.113.42:443",
    ip_address: "203.0.113.42",
    file_hash: null,
    detail: "Outbound HTTPS connection to external IP",
    device_id: "PC-04771",
  },
  {
    id: "evt-006",
    timestamp: "2026-08-26T09:25:00Z",
    source_type: "linux_syslog",
    actor: "root",
    action: "process_start",
    object: "/usr/bin/curl",
    ip_address: null,
    file_hash: null,
    detail: "Curl process started — possible data staging",
    device_id: "SERVER-001",
  },
];

const MOCK_ANOMALIES = [
  {
    id: "anom-001",
    event_ids: ["evt-003", "evt-004"],
    score: 0.87,
    severity: "high",
    category: "data_exfiltration",
    model_name: "isolation_forest",
    model_version: "1.0",
    explanation: { reason: "File hash matches across devices within 5 minutes" },
    review_status: "pending",
    created_at: "2026-08-26T09:30:00Z",
  },
  {
    id: "anom-002",
    event_ids: ["evt-005"],
    score: 0.62,
    severity: "medium",
    category: "suspicious_connection",
    model_name: "isolation_forest",
    model_version: "1.0",
    explanation: { reason: "Outbound connection to external IP after file staging" },
    review_status: "pending",
    created_at: "2026-08-26T09:30:00Z",
  },
];

export default function TimelinePage({
  params,
}: {
  params: { caseId: string };
}) {
  const { status } = useSession();
  const authenticated = status === "authenticated";
  const [filterDevice, setFilterDevice] = useState("");
  const [filterSource, setFilterSource] = useState("");
  const [filterAction, setFilterAction] = useState("");
  const useMock = params.caseId === MOCK_CASE_ID;

  const searchQuery = useQuery({
    queryKey: ["search", params.caseId, { size: 500 }],
    queryFn: () => api.search.query(params.caseId, { size: 500 }),
    enabled: authenticated && !useMock,
  });

  const devicesQuery = useQuery({
    queryKey: ["devices", params.caseId],
    queryFn: () => api.devices.list(params.caseId).catch(() => [] as Device[]),
    enabled: authenticated && !useMock,
  });

  const anomaliesQuery = useQuery({
    queryKey: ["anomalies", params.caseId],
    queryFn: () => api.anomalies.list(params.caseId).catch(() => [] as Anomaly[]),
    enabled: authenticated && !useMock,
  });

  const events = useMock ? MOCK_EVENTS : (searchQuery.data?.events ?? []);
  const devices = useMock ? [] : (devicesQuery.data ?? []);
  const anomalies = useMock ? MOCK_ANOMALIES : (anomaliesQuery.data ?? []);
  const loading = useMock ? false : (!authenticated || searchQuery.isPending);

  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      if (filterDevice && e.device_id !== filterDevice) return false;
      if (filterSource && e.source_type !== filterSource) return false;
      if (filterAction && e.action !== filterAction) return false;
      return true;
    });
  }, [events, filterDevice, filterSource, filterAction]);

  const sourceTypes = useMemo(
    () => [...new Set(events.map((e) => e.source_type))].sort(),
    [events]
  );

  const actionTypes = useMemo(
    () => [...new Set(events.map((e) => e.action))].sort(),
    [events]
  );

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="font-display text-xl font-semibold">Timeline</h1>
        <p className="text-sm text-fog-200/50 mt-1">
          {useMock
            ? "Showing mock data for visual verification (D14e). No real events in this case yet."
            : "Chronological view of all events across devices. Hover for details, click for full event info."}
        </p>
      </div>

      <div className="flex flex-wrap gap-3 mb-6">
        <select
          value={filterDevice}
          onChange={(e) => setFilterDevice(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-fog-200 focus:outline-none focus:ring-2 focus:ring-trace-cyan"
        >
          <option value="">All Devices</option>
          {devices.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name || d.device_type} ({d.device_type})
            </option>
          ))}
        </select>

        <select
          value={filterSource}
          onChange={(e) => setFilterSource(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-fog-200 focus:outline-none focus:ring-2 focus:ring-trace-cyan"
        >
          <option value="">All Sources</option>
          {sourceTypes.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <select
          value={filterAction}
          onChange={(e) => setFilterAction(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-fog-200 focus:outline-none focus:ring-2 focus:ring-trace-cyan"
        >
          <option value="">All Actions</option>
          {actionTypes.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>

        <div className="text-sm text-fog-200/50 flex items-center">
          {filteredEvents.length} of {events.length} events
        </div>
      </div>

      <div className="bg-slate-800 border border-slate-600 rounded-lg p-4">
        <Timeline events={filteredEvents} anomalies={anomalies} loading={loading} />
      </div>

      {useMock && (
        <div className="mt-4 p-3 rounded bg-evidence-amber/10 border border-evidence-amber/30 text-sm text-evidence-amber">
          Mock data active — 6 events across 3 devices, 2 anomalies flagged.
          This is for visual verification of D14(e) only. Remove this route
          once real Scenario 1 data is ingested.
        </div>
      )}
    </div>
  );
}
