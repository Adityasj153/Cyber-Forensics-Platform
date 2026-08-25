"use client";

import { useEffect, useState } from "react";
import { api, LogEvent } from "@/lib/api-client";

const PAGE_SIZE = 50;

export default function SearchPage({
  params,
}: {
  params: { caseId: string };
}) {
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [action, setAction] = useState("");
  const [ipAddress, setIpAddress] = useState("");
  const [timestampFrom, setTimestampFrom] = useState("");
  const [timestampTo, setTimestampTo] = useState("");
  const [offset, setOffset] = useState(0);

  const fetchEvents = async (off = offset) => {
    setLoading(true);
    try {
      const result = await api.search.query(params.caseId, {
        query: query || undefined,
        source_type: sourceType || undefined,
        action: action || undefined,
        ip_address: ipAddress || undefined,
        timestamp_from: timestampFrom || undefined,
        timestamp_to: timestampTo || undefined,
        offset: off,
        size: PAGE_SIZE,
      });
      setEvents(result.events);
      setTotal(result.total);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    fetchEvents(0);
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="font-display text-xl font-semibold">Search Logs</h1>
        <p className="text-sm text-fog-200/50 mt-1">
          Full-text and filtered search across all ingested log events.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="bg-slate-800 border border-slate-600 rounded-lg p-4 mb-6"
      >
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium uppercase tracking-wider mb-1">
              Keyword
            </label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search in actor, action, object, detail..."
              className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-trace-cyan"
            />
          </div>
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider mb-1">
              Source Type
            </label>
            <select
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 text-sm focus:outline-none focus:ring-2 focus:ring-trace-cyan"
            >
              <option value="">All</option>
              <option value="windows_evtx">Windows EVTX</option>
              <option value="linux_syslog">Linux Syslog</option>
              <option value="android_logcat">Android Logcat</option>
              <option value="android_usb_bt">Android USB/BT</option>
              <option value="email_headers">Email Headers</option>
              <option value="network_generic">Network/Generic</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider mb-1">
              Action
            </label>
            <input
              type="text"
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="e.g., file_transfer"
              className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 text-sm focus:outline-none focus:ring-2 focus:ring-trace-cyan"
            />
          </div>
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider mb-1">
              IP Address
            </label>
            <input
              type="text"
              value={ipAddress}
              onChange={(e) => setIpAddress(e.target.value)}
              placeholder="e.g., 192.168.1.1"
              className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-trace-cyan"
            />
          </div>
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider mb-1">
              From
            </label>
            <input
              type="datetime-local"
              value={timestampFrom}
              onChange={(e) => setTimestampFrom(e.target.value)}
              className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 text-sm focus:outline-none focus:ring-2 focus:ring-trace-cyan"
            />
          </div>
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider mb-1">
              To
            </label>
            <input
              type="datetime-local"
              value={timestampTo}
              onChange={(e) => setTimestampTo(e.target.value)}
              className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 text-sm focus:outline-none focus:ring-2 focus:ring-trace-cyan"
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={loading}
              className="bg-trace-cyan text-ink-950 px-6 py-2 rounded text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </div>
        </div>
      </form>

      <div className="text-sm text-fog-200/60 mb-3">{total} events found</div>

      <div className="bg-slate-800 border border-slate-600 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-600 text-xs font-medium uppercase tracking-wider text-fog-200/60">
              <th className="px-4 py-3 text-left">Timestamp</th>
              <th className="px-4 py-3 text-left">Source</th>
              <th className="px-4 py-3 text-left">Action</th>
              <th className="px-4 py-3 text-left">Actor</th>
              <th className="px-4 py-3 text-left">Object</th>
              <th className="px-4 py-3 text-left">IP</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event, idx) => (
              <tr
                key={event.id}
                className={`border-b border-slate-600/50 ${
                  idx % 2 === 1 ? "bg-fog-200/[0.04]" : ""
                }`}
              >
                <td className="px-4 py-2 font-mono text-xs whitespace-nowrap">
                  {new Date(event.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-2">
                  <span className="inline-block bg-slate-600/50 text-fog-200/80 px-2 py-0.5 rounded text-xs">
                    {event.source_type}
                  </span>
                </td>
                <td className="px-4 py-2 font-mono text-xs">{event.action}</td>
                <td className="px-4 py-2 font-mono text-xs">
                  {event.actor || "-"}
                </td>
                <td className="px-4 py-2 font-mono text-xs max-w-[200px] truncate">
                  {event.object || "-"}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-trace-cyan">
                  {event.ip_address || "-"}
                </td>
              </tr>
            ))}
            {events.length === 0 && !loading && (
              <tr>
                <td
                  colSpan={6}
                  className="px-4 py-8 text-center text-fog-200/40"
                >
                  No events found. Upload log files to begin searching.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {total > PAGE_SIZE && (
        <div className="flex justify-between items-center mt-4">
          <button
            onClick={() => {
              const newOffset = Math.max(0, offset - PAGE_SIZE);
              setOffset(newOffset);
              fetchEvents(newOffset);
            }}
            disabled={offset === 0}
            className="bg-slate-600 text-fog-200 px-4 py-2 rounded text-sm disabled:opacity-30 hover:opacity-80"
          >
            Previous
          </button>
          <span className="text-sm text-fog-200/60">
            {offset + 1}-{Math.min(offset + PAGE_SIZE, total)} of {total}
          </span>
          <button
            onClick={() => {
              const newOffset = offset + PAGE_SIZE;
              setOffset(newOffset);
              fetchEvents(newOffset);
            }}
            disabled={offset + PAGE_SIZE >= total}
            className="bg-slate-600 text-fog-200 px-4 py-2 rounded text-sm disabled:opacity-30 hover:opacity-80"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
