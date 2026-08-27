"use client";

import { useEffect, useRef, useState, useMemo, useCallback } from "react";
import * as d3 from "d3";
import { Entity, CorrelationEdge } from "@/lib/api-client";

interface CorrelationGraphProps {
  entities: Entity[];
  edges: CorrelationEdge[];
  loading: boolean;
}

const ENTITY_COLORS: Record<string, string> = {
  device: "#33415A",
  file: "#C9D2E0",
  ip: "#4FB8C4",
  user: "#D98E33",
};

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  type: string;
  color: string;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  id: string;
  relation: string;
  confidence: number;
}

export default function CorrelationGraph({
  entities,
  edges,
  loading,
}: CorrelationGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<CorrelationEdge | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const graphData = useMemo(() => {
    const nodeMap = new Map<string, GraphNode>();
    entities.forEach((e) => {
      nodeMap.set(e.id, {
        id: e.id,
        label: e.value,
        type: e.entity_type,
        color: ENTITY_COLORS[e.entity_type] || "#6B8AAE",
      });
    });

    const links: GraphLink[] = edges.map((e) => ({
      id: e.id,
      source: e.entity_a_id,
      target: e.entity_b_id,
      relation: e.relation_type,
      confidence: e.confidence,
    }));

    const connectedIds = new Set<string>();
    links.forEach((l) => {
      connectedIds.add(l.source as string);
      connectedIds.add(l.target as string);
    });

    const nodes = Array.from(nodeMap.values()).filter((n) =>
      connectedIds.has(n.id)
    );

    return { nodes, links };
  }, [entities, edges]);

  const render = useCallback(() => {
    if (!svgRef.current || !containerRef.current) return;
    if (graphData.nodes.length === 0) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = Math.max(500, container.clientHeight);

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("width", width).attr("height", height);

    const g = svg.append("g");

    // Zoom
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });
    svg.call(zoom);

    // Arrow markers
    const defs = svg.append("defs");
    Object.entries(ENTITY_COLORS).forEach(([type, color]) => {
      defs
        .append("marker")
        .attr("id", `arrow-${type}`)
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 20)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", color)
        .attr("opacity", 0.6);
    });

    // Simulation
    const simulation = d3
      .forceSimulation<GraphNode>(graphData.nodes)
      .force(
        "link",
        d3
          .forceLink<GraphNode, GraphLink>(graphData.links)
          .id((d) => d.id)
          .distance(120)
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(30));

    simulationRef.current = simulation;

    // ── Custody-thread edges: dotted lines, cyan/amber by confidence ──
    const link = g
      .append("g")
      .selectAll<SVGLineElement, GraphLink>("line")
      .data(graphData.links)
      .join("line")
      .attr("stroke", (d) => (d.confidence >= 0.7 ? "#4FB8C4" : "#D98E33"))
      .attr("stroke-width", (d) => Math.max(1.5, d.confidence * 3))
      .attr("stroke-dasharray", "4,3")
      .attr("stroke-opacity", (d) => Math.max(0.4, d.confidence))
      .attr("marker-end", (d) => {
        const targetNode = graphData.nodes.find(
          (n) => n.id === (d.target as string)
        );
        return targetNode
          ? `url(#arrow-${targetNode.type})`
          : "url(#arrow-device)";
      });

    // ── Nodes ──
    const node = g
      .append("g")
      .selectAll<SVGGElement, GraphNode>("g")
      .data(graphData.nodes)
      .join("g")
      .attr("cursor", "pointer")
      .call(
        d3
          .drag<SVGGElement, GraphNode>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    // Node shapes — per design.md §3.3
    node.each(function (d) {
      const el = d3.select(this);
      const size = 10;
      const color = d.color;

      switch (d.type) {
        case "device":
          // Slate filled rect
          el.append("rect")
            .attr("x", -size)
            .attr("y", -size)
            .attr("width", size * 2)
            .attr("height", size * 2)
            .attr("rx", 2)
            .attr("fill", color)
            .attr("opacity", 0.9);
          break;
        case "file":
          // Fog filled diamond
          el.append("polygon")
            .attr(
              "points",
              `0,${-size} ${size},0 0,${size} ${-size},0`
            )
            .attr("fill", color)
            .attr("opacity", 0.9);
          break;
        case "ip":
          // Trace-cyan filled triangle
          el.append("polygon")
            .attr(
              "points",
              `0,${-size} ${size * 0.9},${size * 0.6} ${-size * 0.9},${size * 0.6}`
            )
            .attr("fill", color)
            .attr("opacity", 0.9);
          break;
        case "hash":
          // Purple filled hexagon
          el.append("polygon")
            .attr(
              "points",
              `0,${-size} ${size * 0.87},${-size * 0.5} ${size * 0.87},${size * 0.5} 0,${size} ${-size * 0.87},${size * 0.5} ${-size * 0.87},${-size * 0.5}`
            )
            .attr("fill", color)
            .attr("opacity", 0.9);
          break;
        case "user":
          // Amber outline only — transparent fill
          el.append("circle")
            .attr("r", size)
            .attr("fill", "none")
            .attr("stroke", color)
            .attr("stroke-width", 2)
            .attr("opacity", 0.9);
          break;
        default:
          el.append("circle")
            .attr("r", size)
            .attr("fill", color)
            .attr("opacity", 0.9);
      }
    });

    // Labels
    node
      .append("text")
      .attr("dy", 22)
      .attr("text-anchor", "middle")
      .attr("fill", "#C9D2E0")
      .attr("font-size", "9px")
      .attr("font-family", "JetBrains Mono, monospace")
      .text((d) => {
        const label = d.label;
        return label.length > 20 ? label.slice(0, 20) + "…" : label;
      });

    // Node type badge
    node
      .append("text")
      .attr("dy", -16)
      .attr("text-anchor", "middle")
      .attr("fill", (d) => d.color)
      .attr("font-size", "7px")
      .attr("font-weight", "600")
      .attr("letter-spacing", "0.05em")
      .text((d) => d.type);

    // Interactions
    node
      .on("click", (event, d) => {
        event.stopPropagation();
        setSelectedNode(d);
      })
      .on("mouseenter", (_, d) => setHoveredNode(d.id))
      .on("mouseleave", () => setHoveredNode(null));

    link.on("click", (event, d) => {
      event.stopPropagation();
      const edge = edges.find((e) => e.id === d.id);
      if (edge) setSelectedEdge(edge);
    });

    svg.on("click", () => {
      setSelectedNode(null);
      setSelectedEdge(null);
    });

    // Tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as GraphNode).x!)
        .attr("y1", (d) => (d.source as GraphNode).y!)
        .attr("x2", (d) => (d.target as GraphNode).x!)
        .attr("y2", (d) => (d.target as GraphNode).y!);

      node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });
  }, [graphData, edges]);

  useEffect(() => {
    render();
    return () => {
      simulationRef.current?.stop();
    };
  }, [render]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-fog-200/40">
        Loading correlation graph...
      </div>
    );
  }

  if (graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-fog-200/40">
        No correlations found. Run the AI engine on ingested logs first.
      </div>
    );
  }

  return (
    <div className="relative">
      <div ref={containerRef} className="w-full" style={{ minHeight: 500 }}>
        <svg ref={svgRef} className="w-full" />
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-4 px-4 text-xs text-fog-200/60">
        {Object.entries(ENTITY_COLORS).map(([key, color]) => (
          <div key={key} className="flex items-center gap-1.5">
            {key === "user" ? (
              <svg width="12" height="12" viewBox="0 0 12 12">
                <circle cx="6" cy="6" r="5" fill="none" stroke={color} strokeWidth="2" />
              </svg>
            ) : (
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: color }}
              />
            )}
            {key}
          </div>
        ))}
        <div className="border-l border-slate-600 pl-4 flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <svg width="24" height="12" viewBox="0 0 24 12">
              <line x1="0" y1="6" x2="24" y2="6" stroke="#4FB8C4" strokeWidth="1.5" strokeDasharray="4,3" />
            </svg>
            Confirmed (≥70%)
          </div>
          <div className="flex items-center gap-1.5">
            <svg width="24" height="12" viewBox="0 0 24 12">
              <line x1="0" y1="6" x2="24" y2="6" stroke="#D98E33" strokeWidth="1.5" strokeDasharray="4,3" />
            </svg>
            Inferred (&lt;70%)
          </div>
        </div>
      </div>

      {/* Node Detail */}
      {selectedNode && (
        <div className="fixed inset-0 z-50 bg-ink-950/80 flex items-center justify-center p-4">
          <div className="bg-slate-800 border border-slate-600 rounded-lg p-6 max-w-md w-full">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display text-lg font-semibold">Entity Detail</h3>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-fog-200/40 hover:text-fog-200 text-lg"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3 text-sm">
              <div>
                <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-0.5">
                  Type
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-sm"
                    style={{ backgroundColor: selectedNode.color }}
                  />
                  <span className="text-fog-200 capitalize">
                    {selectedNode.type}
                  </span>
                </div>
              </div>
              <div>
                <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-0.5">
                  Value
                </div>
                <div className="text-fog-200 font-mono break-all">
                  {selectedNode.label}
                </div>
              </div>
              <div>
                <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-0.5">
                  Connected Edges
                </div>
                <div className="text-fog-200">
                  {edges.filter(
                    (e) =>
                      e.entity_a_id === selectedNode.id ||
                      e.entity_b_id === selectedNode.id
                  ).length}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edge Detail */}
      {selectedEdge && (
        <div className="fixed inset-0 z-50 bg-ink-950/80 flex items-center justify-center p-4">
          <div className="bg-slate-800 border border-slate-600 rounded-lg p-6 max-w-lg w-full">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display text-lg font-semibold">
                Correlation Detail
              </h3>
              <button
                onClick={() => setSelectedEdge(null)}
                className="text-fog-200/40 hover:text-fog-200 text-lg"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3 text-sm">
              <div>
                <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-0.5">
                  Relation
                </div>
                <div className="text-fog-200">{selectedEdge.relation_type}</div>
              </div>
              <div>
                <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-0.5">
                  Confidence
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-ink-950 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full bg-trace-cyan rounded-full"
                      style={{ width: `${selectedEdge.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-fog-200 font-mono text-xs">
                    {(selectedEdge.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              {selectedEdge.explanation && (
                <div>
                  <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-0.5">
                    Explanation
                  </div>
                  <pre className="bg-ink-950 rounded p-3 text-xs font-mono text-fog-200/70 overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(selectedEdge.explanation, null, 2)}
                  </pre>
                </div>
              )}
              <div>
                <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-0.5">
                  Evidence Events
                </div>
                <div className="text-fog-200 font-mono text-xs">
                  {selectedEdge.evidence_event_ids.length} events
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
