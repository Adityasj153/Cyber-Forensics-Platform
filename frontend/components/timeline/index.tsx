"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import * as d3 from "d3";
import { LogEvent, Anomaly } from "@/lib/api-client";

interface TimelineProps {
  events: LogEvent[];
  anomalies?: Anomaly[];
  loading: boolean;
}

const SOURCE_COLORS: Record<string, string> = {
  windows_evtx: "#4FB8C4",
  linux_syslog: "#5FA777",
  android_logcat: "#D98E33",
  android_usb_bt: "#C9483F",
  email_headers: "#9B7ED8",
  network_generic: "#6B8AAE",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#C9483F",
  high: "#C9483F",
  medium: "#D98E33",
  low: "#4FB8C4",
};

const ACTION_ICONS: Record<string, string> = {
  file_transfer: "↗",
  usb_transfer: "⊕",
  bluetooth_transfer: "◎",
  email_sent: "✉",
  logon: "→",
  logoff: "←",
  process_start: "▶",
  file_write: "✎",
  file_delete: "✕",
  network_connection: "⇄",
  connection_blocked: "⊘",
  error: "!",
};

export default function Timeline({ events, anomalies = [], loading }: TimelineProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    event: LogEvent;
  } | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<LogEvent | null>(null);

  const sortedEvents = useMemo(
    () =>
      [...events].sort(
        (a, b) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      ),
    [events]
  );

  const timeExtent = useMemo(() => {
    if (sortedEvents.length === 0) return null;
    return d3.extent(sortedEvents, (d) => new Date(d.timestamp)) as [Date, Date];
  }, [sortedEvents]);

  const anomalyEventIds = useMemo(() => {
    const ids = new Set<string>();
    anomalies.forEach((a) => a.event_ids.forEach((id) => ids.add(id)));
    return ids;
  }, [anomalies]);

  const devices = useMemo(() => {
    const map = new Map<string, LogEvent[]>();
    sortedEvents.forEach((e) => {
      const key = e.device_id || e.source_type || "unknown";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(e);
    });
    return Array.from(map.entries());
  }, [sortedEvents]);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || sortedEvents.length === 0)
      return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const rowHeight = 40;
    const margin = { top: 40, right: 30, bottom: 30, left: 140 };
    const height = margin.top + devices.length * rowHeight + margin.bottom;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("width", width).attr("height", height);

    if (!timeExtent) return;

    const xScale = d3
      .scaleTime()
      .domain(timeExtent)
      .range([margin.left, width - margin.right]);

    // Grid lines
    const xAxis = d3
      .axisTop(xScale)
      .ticks(width > 800 ? 10 : 5)
      .tickSize(-(height - margin.top - margin.bottom));

    svg
      .append("g")
      .attr("transform", `translate(0,${margin.top})`)
      .call(xAxis)
      .call((g) => {
        g.select(".domain").remove();
        g.selectAll(".tick line")
          .attr("stroke", "#33415A")
          .attr("stroke-dasharray", "2,2");
        g.selectAll(".tick text")
          .attr("fill", "#C9D2E0")
          .attr("font-size", "10px")
          .attr("font-family", "JetBrains Mono, monospace");
      });

    // Device rows
    const yScale = d3
      .scaleBand()
      .domain(devices.map(([key]) => key))
      .range([margin.top, height - margin.bottom])
      .padding(0.3);

    devices.forEach(([deviceKey, deviceEvents], rowIdx) => {
      const y = yScale(deviceKey)!;
      const rowColor = SOURCE_COLORS[deviceEvents[0]?.source_type] || "#6B8AAE";

      // Row background
      svg
        .append("rect")
        .attr("x", margin.left)
        .attr("y", y)
        .attr("width", width - margin.left - margin.right)
        .attr("height", yScale.bandwidth())
        .attr("fill", rowIdx % 2 === 0 ? "#1A223320" : "transparent")
        .attr("rx", 4);

      // Device label
      svg
        .append("text")
        .attr("x", margin.left - 10)
        .attr("y", y + yScale.bandwidth() / 2)
        .attr("text-anchor", "end")
        .attr("dominant-baseline", "central")
        .attr("fill", rowColor)
        .attr("font-size", "11px")
        .attr("font-weight", "500")
        .text(deviceKey.length > 18 ? deviceKey.slice(0, 18) + "…" : deviceKey);

      // ── Custody thread: dotted lines between consecutive events ──
      const cy = y + yScale.bandwidth() / 2;
      for (let i = 0; i < deviceEvents.length - 1; i++) {
        const curr = deviceEvents[i];
        const next = deviceEvents[i + 1];
        const x1 = xScale(new Date(curr.timestamp));
        const x2 = xScale(new Date(next.timestamp));

        const currIsAnomaly = anomalyEventIds.has(curr.id);
        const nextIsAnomaly = anomalyEventIds.has(next.id);

        // Amber if either event is anomaly (inferred link), cyan otherwise (confirmed)
        const lineColor =
          currIsAnomaly || nextIsAnomaly ? "#D98E33" : "#4FB8C4";

        // Opacity stepped by time gap: tighter = more confident
        const timeGapMs = new Date(next.timestamp).getTime() - new Date(curr.timestamp).getTime();
        const maxGap = timeExtent[1].getTime() - timeExtent[0].getTime();
        const gapRatio = maxGap > 0 ? timeGapMs / maxGap : 0;
        const lineOpacity = Math.max(0.3, 1 - gapRatio * 0.6);

        svg
          .append("line")
          .attr("x1", x1)
          .attr("x2", x2)
          .attr("y1", cy)
          .attr("y2", cy)
          .attr("stroke", lineColor)
          .attr("stroke-width", 1.5)
          .attr("stroke-dasharray", "4,3")
          .attr("opacity", lineOpacity);
      }

      // ── Event markers ──
      deviceEvents.forEach((event) => {
        const cx = xScale(new Date(event.timestamp));
        const isAnomaly = anomalyEventIds.has(event.id);
        const icon = ACTION_ICONS[event.action] || "·";

        const g = svg.append("g").attr("class", "event-marker");

        // Hit area (always a circle for easy targeting)
        g.append("circle")
          .attr("cx", cx)
          .attr("cy", cy)
          .attr("r", 12)
          .attr("fill", "transparent")
          .attr("cursor", "pointer")
          .on("mouseenter", (mouseEvent) => {
            const rect = container.getBoundingClientRect();
            setTooltip({
              x: mouseEvent.clientX - rect.left,
              y: mouseEvent.clientY - rect.top,
              event,
            });
          })
          .on("mouseleave", () => setTooltip(null))
          .on("click", () => setSelectedEvent(event));

        if (isAnomaly) {
          // ── Triangle marker for anomalies ──
          const severity = event.source_type.includes("critical")
            ? "critical"
            : "medium";
          const triColor = SEVERITY_COLORS[severity] || "#D98E33";
          const size = 7;

          // Equilateral triangle pointing up
          const points = [
            [cx, cy - size],
            [cx - size * 0.866, cy + size * 0.5],
            [cx + size * 0.866, cy + size * 0.5],
          ]
            .map((p) => p.join(","))
            .join(" ");

          g.append("polygon")
            .attr("points", points)
            .attr("fill", triColor)
            .attr("opacity", 0.9)
            .attr("stroke", triColor)
            .attr("stroke-width", 1.5)
            .attr("stroke-opacity", 0.3);
        } else {
          // ── Circle marker for confirmed events ──
          const color = SOURCE_COLORS[event.source_type] || "#6B8AAE";

          g.append("circle")
            .attr("cx", cx)
            .attr("cy", cy)
            .attr("r", 5)
            .attr("fill", color)
            .attr("opacity", 0.9)
            .attr("stroke", color)
            .attr("stroke-width", 1.5)
            .attr("stroke-opacity", 0.3);
        }

        // Action icon
        g.append("text")
          .attr("x", cx)
          .attr("y", cy)
          .attr("text-anchor", "middle")
          .attr("dominant-baseline", "central")
          .attr("fill", "#fff")
          .attr("font-size", "7px")
          .attr("pointer-events", "none")
          .text(icon);
      });
    });

    // Now line (if within range)
    const now = new Date();
    if (now >= timeExtent[0] && now <= timeExtent[1]) {
      svg
        .append("line")
        .attr("x1", xScale(now))
        .attr("x2", xScale(now))
        .attr("y1", margin.top)
        .attr("y2", height - margin.bottom)
        .attr("stroke", "#C9483F")
        .attr("stroke-width", 1)
        .attr("stroke-dasharray", "4,4")
        .attr("opacity", 0.5);
    }
  }, [sortedEvents, devices, timeExtent, anomalyEventIds]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-fog-200/40">
        Loading timeline...
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-fog-200/40">
        No events to display. Upload and parse log files to build a timeline.
      </div>
    );
  }

  return (
    <div className="relative">
      <div ref={containerRef} className="w-full overflow-x-auto">
        <svg ref={svgRef} className="select-none" />
      </div>

      {tooltip && (
        <div
          className="absolute z-50 bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-xl pointer-events-none max-w-xs"
          style={{ left: tooltip.x + 12, top: tooltip.y - 8 }}
        >
          <div className="text-xs font-mono text-fog-200/60 mb-1">
            {new Date(tooltip.event.timestamp).toLocaleString()}
          </div>
          <div className="text-sm font-medium text-fog-200">
            {tooltip.event.action}
          </div>
          {tooltip.event.actor && (
            <div className="text-xs text-fog-200/60 mt-1">
              Actor: <span className="font-mono">{tooltip.event.actor}</span>
            </div>
          )}
          {tooltip.event.object && (
            <div className="text-xs text-fog-200/60">
              Object: <span className="font-mono">{tooltip.event.object}</span>
            </div>
          )}
          {tooltip.event.ip_address && (
            <div className="text-xs text-trace-cyan font-mono">
              IP: {tooltip.event.ip_address}
            </div>
          )}
          {tooltip.event.file_hash && (
            <div className="text-xs text-evidence-amber font-mono mt-1">
              Hash: {tooltip.event.file_hash.slice(0, 16)}...
            </div>
          )}
        </div>
      )}

      {selectedEvent && (
        <div className="fixed inset-0 z-50 bg-ink-950/80 flex items-center justify-center p-4">
          <div className="bg-slate-800 border border-slate-600 rounded-lg p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display text-lg font-semibold">Event Detail</h3>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-fog-200/40 hover:text-fog-200 text-lg"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3 text-sm">
              <Row label="Timestamp" value={new Date(selectedEvent.timestamp).toLocaleString()} />
              <Row label="Source" value={selectedEvent.source_type} />
              <Row label="Action" value={selectedEvent.action} />
              {selectedEvent.actor && <Row label="Actor" value={selectedEvent.actor} mono />}
              {selectedEvent.object && <Row label="Object" value={selectedEvent.object} mono />}
              {selectedEvent.ip_address && (
                <Row label="IP Address" value={selectedEvent.ip_address} mono highlight />
              )}
              {selectedEvent.file_hash && (
                <Row label="File Hash" value={selectedEvent.file_hash} mono highlight />
              )}
              {selectedEvent.detail && (
                <Row label="Detail" value={selectedEvent.detail} />
              )}
              {selectedEvent.raw_line && (
                <div>
                  <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-1">
                    Raw Line
                  </div>
                  <pre className="bg-ink-950 rounded p-3 text-xs font-mono text-fog-200/70 overflow-x-auto whitespace-pre-wrap">
                    {selectedEvent.raw_line}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-4 px-4 text-xs text-fog-200/60">
        {/* Source type colors */}
        {Object.entries(SOURCE_COLORS).map(([key, color]) => (
          <div key={key} className="flex items-center gap-1.5">
            <div
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: color }}
            />
            {key.replace("_", " ")}
          </div>
        ))}
        {/* Separator */}
        <div className="border-l border-slate-600 pl-4 flex items-center gap-4">
          {/* Confirmed marker */}
          <div className="flex items-center gap-1.5">
            <svg width="12" height="12" viewBox="0 0 12 12">
              <circle cx="6" cy="6" r="4" fill="#4FB8C4" />
            </svg>
            Confirmed
          </div>
          {/* Anomaly marker */}
          <div className="flex items-center gap-1.5">
            <svg width="12" height="12" viewBox="0 0 12 12">
              <polygon points="6,1 1,11 11,11" fill="#D98E33" />
            </svg>
            Anomaly
          </div>
          {/* Custody thread */}
          <div className="flex items-center gap-1.5">
            <svg width="24" height="12" viewBox="0 0 24 12">
              <line x1="0" y1="6" x2="24" y2="6" stroke="#4FB8C4" strokeWidth="1.5" strokeDasharray="4,3" />
            </svg>
            Custody thread
          </div>
          <div className="flex items-center gap-1.5">
            <svg width="24" height="12" viewBox="0 0 24 12">
              <line x1="0" y1="6" x2="24" y2="6" stroke="#D98E33" strokeWidth="1.5" strokeDasharray="4,3" />
            </svg>
            Inferred link
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  mono,
  highlight,
}: {
  label: string;
  value: string;
  mono?: boolean;
  highlight?: boolean;
}) {
  return (
    <div>
      <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-0.5">
        {label}
      </div>
      <div
        className={`${
          mono ? "font-mono" : ""
        } ${highlight ? "text-trace-cyan" : "text-fog-200"} break-all`}
      >
        {value}
      </div>
    </div>
  );
}
