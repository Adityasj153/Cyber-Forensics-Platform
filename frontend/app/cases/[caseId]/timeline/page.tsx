"use client";

import { useEffect, useState, useMemo } from "react";
import { api, LogEvent, Device } from "@/lib/api-client";
import Timeline from "@/components/timeline";

export default function TimelinePage({
  params,
}: {
  params: { caseId: string };
}) {
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterDevice, setFilterDevice] = useState("");
  const [filterSource, setFilterSource] = useState("");
  const [filterAction, setFilterAction] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return;

    Promise.all([
      api.search.query(params.caseId, { size: 500 }),
      api.devices.list(params.caseId).catch(() => []),
    ])
      .then(([searchResult, devs]) => {
        setEvents(searchResult.events);
        setDevices(devs);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [params.caseId]);

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
          Chronological view of all events across devices. Hover for details, click for full event info.
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
        <Timeline events={filteredEvents} loading={loading} />
      </div>
    </div>
  );
}
