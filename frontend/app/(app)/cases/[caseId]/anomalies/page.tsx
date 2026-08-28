"use client";

import { useState, useMemo } from "react";
import { useSession } from "next-auth/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Anomaly } from "@/lib/api-client";
import AnomalyPanel from "@/components/anomaly-panel";

export default function AnomaliesPage({
  params,
}: {
  params: { caseId: string };
}) {
  const { status } = useSession();
  const authenticated = status === "authenticated";
  const queryClient = useQueryClient();
  const [filterSeverity, setFilterSeverity] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const anomaliesQuery = useQuery({
    queryKey: ["anomalies", params.caseId],
    queryFn: () => api.anomalies.list(params.caseId),
    enabled: authenticated,
  });

  const reviewMutation = useMutation({
    mutationFn: ({
      id,
      reviewStatus,
    }: {
      id: string;
      reviewStatus: "confirmed" | "dismissed";
    }) => api.anomalies.review(params.caseId, id, reviewStatus),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["anomalies", params.caseId] }),
    onError: console.error,
  });

  const anomalies: Anomaly[] = anomaliesQuery.data ?? [];
  const loading = !authenticated || anomaliesQuery.isPending;

  const handleReview = (
    id: string,
    reviewStatus: "confirmed" | "dismissed"
  ) => {
    reviewMutation.mutate({ id, reviewStatus });
  };

  const filtered = useMemo(() => {
    return anomalies.filter((a) => {
      if (filterSeverity && a.severity !== filterSeverity) return false;
      if (filterCategory && a.category !== filterCategory) return false;
      if (filterStatus && a.review_status !== filterStatus) return false;
      return true;
    });
  }, [anomalies, filterSeverity, filterCategory, filterStatus]);

  const categories = useMemo(
    () => [...new Set(anomalies.map((a) => a.category))].sort(),
    [anomalies]
  );

  const stats = useMemo(() => {
    const total = anomalies.length;
    const pending = anomalies.filter((a) => a.review_status === "pending").length;
    const confirmed = anomalies.filter((a) => a.review_status === "confirmed").length;
    const critical = anomalies.filter((a) => a.severity === "critical").length;
    return { total, pending, confirmed, critical };
  }, [anomalies]);

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="font-display text-xl font-semibold">Anomalies & Alerts</h1>
        <p className="text-sm text-fog-200/50 mt-1">
          AI-detected anomalies with explainability. Review and confirm/dismiss each finding.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3">
          <div className="text-xs text-fog-200/40 uppercase tracking-wider">
            Total
          </div>
          <div className="text-2xl font-semibold text-fog-200 mt-1">
            {stats.total}
          </div>
        </div>
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3">
          <div className="text-xs text-evidence-amber uppercase tracking-wider">
            Pending Review
          </div>
          <div className="text-2xl font-semibold text-evidence-amber mt-1">
            {stats.pending}
          </div>
        </div>
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3">
          <div className="text-xs text-verified uppercase tracking-wider">
            Confirmed
          </div>
          <div className="text-2xl font-semibold text-verified mt-1">
            {stats.confirmed}
          </div>
        </div>
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3">
          <div className="text-xs text-critical uppercase tracking-wider">
            Critical
          </div>
          <div className="text-2xl font-semibold text-critical mt-1">
            {stats.critical}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-fog-200 focus:outline-none focus:ring-2 focus:ring-trace-cyan"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-fog-200 focus:outline-none focus:ring-2 focus:ring-trace-cyan"
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c.replace(/_/g, " ")}
            </option>
          ))}
        </select>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-fog-200 focus:outline-none focus:ring-2 focus:ring-trace-cyan"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="confirmed">Confirmed</option>
          <option value="dismissed">Dismissed</option>
        </select>

        <span className="text-sm text-fog-200/40 flex items-center">
          {filtered.length} of {anomalies.length} anomalies
        </span>
      </div>

      {/* Anomaly List */}
      <div className="space-y-2">
        {loading ? (
          <div className="text-center py-12 text-fog-200/40">
            Loading anomalies...
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-slate-800 border border-slate-600 rounded-lg p-8 text-center">
            <p className="text-fog-200/60">
              {anomalies.length === 0
                ? "No anomalies detected yet. Run the AI engine on ingested logs first."
                : "No anomalies match the current filters."}
            </p>
          </div>
        ) : (
          filtered.map((anomaly) => (
            <AnomalyPanel
              key={anomaly.id}
              anomaly={anomaly}
              onReview={handleReview}
            />
          ))
        )}
      </div>
    </div>
  );
}
