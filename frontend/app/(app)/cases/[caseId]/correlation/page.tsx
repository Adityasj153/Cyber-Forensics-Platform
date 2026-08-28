"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import { api, Entity, CorrelationEdge } from "@/lib/api-client";
import CorrelationGraph from "@/components/correlation-graph";

export default function CorrelationPage({
  params,
}: {
  params: { caseId: string };
}) {
  const { status } = useSession();
  const authenticated = status === "authenticated";
  const [minConfidence, setMinConfidence] = useState(0);
  const [view, setView] = useState<"graph" | "list">("graph");

  const entitiesQuery = useQuery({
    queryKey: ["entities", params.caseId],
    queryFn: () => api.entities.list(params.caseId),
    enabled: authenticated,
  });

  const correlationsQuery = useQuery({
    queryKey: ["correlations", params.caseId],
    queryFn: () => api.correlations.list(params.caseId),
    enabled: authenticated,
  });

  const entities: Entity[] = entitiesQuery.data ?? [];
  const edges: CorrelationEdge[] = correlationsQuery.data ?? [];
  const loading =
    !authenticated || entitiesQuery.isPending || correlationsQuery.isPending;

  const filteredEdges = edges.filter((e) => e.confidence >= minConfidence);

  const entityMap = new Map(entities.map((e) => [e.id, e]));

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-xl font-semibold">
            Correlation Graph
          </h1>
          <p className="text-sm text-fog-200/50 mt-1">
            Interactive view of entity relationships. Drag nodes, zoom, click for details.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-slate-800 border border-slate-600 rounded overflow-hidden">
            <button
              onClick={() => setView("graph")}
              className={`px-3 py-1.5 text-xs font-medium ${
                view === "graph"
                  ? "bg-trace-cyan text-ink-950"
                  : "text-fog-200/60 hover:text-fog-200"
              }`}
            >
              Graph
            </button>
            <button
              onClick={() => setView("list")}
              className={`px-3 py-1.5 text-xs font-medium ${
                view === "list"
                  ? "bg-trace-cyan text-ink-950"
                  : "text-fog-200/60 hover:text-fog-200"
              }`}
            >
              List
            </button>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <label className="flex items-center gap-2 text-sm text-fog-200/60">
          Min Confidence:
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={minConfidence}
            onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
            className="w-32 accent-trace-cyan"
          />
          <span className="font-mono text-xs text-fog-200">
            {(minConfidence * 100).toFixed(0)}%
          </span>
        </label>
        <span className="text-sm text-fog-200/40">
          {filteredEdges.length} of {edges.length} edges shown
        </span>
      </div>

      <div className="bg-slate-800 border border-slate-600 rounded-lg p-4">
        {view === "graph" ? (
          <CorrelationGraph
            entities={entities}
            edges={filteredEdges}
            loading={loading}
          />
        ) : (
          <div>
            {loading ? (
              <div className="text-center py-12 text-fog-200/40">
                Loading correlations...
              </div>
            ) : filteredEdges.length === 0 ? (
              <div className="text-center py-12 text-fog-200/40">
                No correlations found.
              </div>
            ) : (
              <div className="space-y-2">
                {filteredEdges.map((edge) => {
                  const entityA = entityMap.get(edge.entity_a_id);
                  const entityB = entityMap.get(edge.entity_b_id);
                  return (
                    <div
                      key={edge.id}
                      className="bg-ink-950/50 rounded px-4 py-3"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm">
                          <span className="font-mono text-trace-cyan">
                            {entityA?.value || edge.entity_a_id.slice(0, 8)}
                          </span>
                          <span className="text-fog-200/40">
                            → {edge.relation_type} →
                          </span>
                          <span className="font-mono text-evidence-amber">
                            {entityB?.value || edge.entity_b_id.slice(0, 8)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-20 bg-slate-600 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="h-full bg-trace-cyan rounded-full"
                              style={{
                                width: `${edge.confidence * 100}%`,
                              }}
                            />
                          </div>
                          <span className="text-xs font-mono text-fog-200/60">
                            {(edge.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      {edge.explanation && (
                        <div className="mt-2 text-xs text-fog-200/50">
                          {typeof edge.explanation === "object" &&
                            Object.entries(
                              edge.explanation as Record<string, unknown>
                            ).map(([k, v]) => (
                              <span key={k} className="mr-3">
                                <span className="text-fog-200/40">{k}:</span>{" "}
                                {String(v)}
                              </span>
                            ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
