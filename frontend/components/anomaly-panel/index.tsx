"use client";

import { useState } from "react";
import { Anomaly } from "@/lib/api-client";
import { useRole } from "@/lib/rbac";

interface AnomalyPanelProps {
  anomaly: Anomaly;
  onReview: (id: string, status: "confirmed" | "dismissed") => void;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-critical",
  high: "bg-evidence-amber",
  medium: "bg-trace-cyan",
  low: "bg-fog-200/30",
};

const SEVERITY_TEXT: Record<string, string> = {
  critical: "text-critical",
  high: "text-evidence-amber",
  medium: "text-trace-cyan",
  low: "text-fog-200/60",
};

export default function AnomalyPanel({ anomaly, onReview }: AnomalyPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const role = useRole();
  const canReview = role === "admin" || role === "investigator";

  const explanation = anomaly.explanation as Record<string, unknown> | null;
  const featureImportances = explanation?.feature_importances as
    | Array<{ feature: string; importance: number; value?: unknown }>
    | undefined;
  const reasons = explanation?.reasons as string[] | undefined;

  return (
    <div className="bg-ink-950/50 border border-slate-600/50 rounded-lg overflow-hidden">
      <div
        className="px-4 py-3 cursor-pointer hover:bg-fog-200/[0.03] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`w-2.5 h-2.5 rounded-full ${
                SEVERITY_COLORS[anomaly.severity] || "bg-fog-200/30"
              }`}
            />
            <div>
              <div className="text-sm font-medium text-fog-200">
                {anomaly.category.replace(/_/g, " ")}
              </div>
              <div className="text-xs text-fog-200/40 mt-0.5">
                {anomaly.model_name}
                {anomaly.model_version && ` v${anomaly.model_version}`}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span
              className={`text-xs font-medium uppercase ${
                SEVERITY_TEXT[anomaly.severity] || "text-fog-200/60"
              }`}
            >
              {anomaly.severity}
            </span>
            <div className="flex items-center gap-1">
              <span className="text-xs font-mono text-fog-200/60">
                {(anomaly.score * 100).toFixed(0)}%
              </span>
              <svg
                className={`w-4 h-4 text-fog-200/40 transition-transform ${
                  expanded ? "rotate-180" : ""
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 mt-2">
          <span
            className={`text-xs px-2 py-0.5 rounded ${
              anomaly.review_status === "confirmed"
                ? "bg-verified/20 text-verified"
                : anomaly.review_status === "dismissed"
                ? "bg-fog-200/10 text-fog-200/40"
                : "bg-evidence-amber/20 text-evidence-amber"
            }`}
          >
            {anomaly.review_status}
          </span>
          <span className="text-xs text-fog-200/30">
            {anomaly.event_ids.length} event{anomaly.event_ids.length !== 1 && "s"}
          </span>
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-600/30">
          {/* Confidence Score */}
          <div className="mt-3 mb-4">
            <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-1">
              Confidence Score
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    anomaly.severity === "critical"
                      ? "bg-critical"
                      : anomaly.severity === "high"
                      ? "bg-evidence-amber"
                      : "bg-trace-cyan"
                  }`}
                  style={{ width: `${anomaly.score * 100}%` }}
                />
              </div>
              <span className="text-sm font-mono text-fog-200">
                {(anomaly.score * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* SHAP Explanation - Feature Importances */}
          {featureImportances && featureImportances.length > 0 && (
            <div className="mb-4">
              <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-2">
                Feature Importance (SHAP)
              </div>
              <div className="space-y-1.5">
                {featureImportances
                  .sort((a, b) => Math.abs(b.importance) - Math.abs(a.importance))
                  .slice(0, 8)
                  .map((fi, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div className="w-28 text-xs text-fog-200/60 truncate font-mono">
                        {fi.feature}
                      </div>
                      <div className="flex-1 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            fi.importance > 0 ? "bg-critical" : "bg-verified"
                          }`}
                          style={{
                            width: `${Math.min(
                              100,
                              Math.abs(fi.importance) * 100
                            )}%`,
                          }}
                        />
                      </div>
                      <div className="w-16 text-xs font-mono text-fog-200/50 text-right">
                        {fi.importance > 0 ? "+" : ""}
                        {fi.importance.toFixed(3)}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Rule-based Reasons */}
          {reasons && reasons.length > 0 && (
            <div className="mb-4">
              <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-2">
                Reasons
              </div>
              <ul className="space-y-1">
                {reasons.map((reason, i) => (
                  <li
                    key={i}
                    className="text-xs text-fog-200/70 flex items-start gap-2"
                  >
                    <span className="text-evidence-amber mt-0.5">•</span>
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Raw Explanation */}
          {!featureImportances && !reasons && explanation && (
            <div className="mb-4">
              <div className="text-xs text-fog-200/40 uppercase tracking-wider mb-2">
                Explanation
              </div>
              <pre className="bg-slate-800 rounded p-3 text-xs font-mono text-fog-200/70 overflow-x-auto whitespace-pre-wrap max-h-48">
                {JSON.stringify(explanation, null, 2)}
              </pre>
            </div>
          )}

          {/* Review Actions */}
          {anomaly.review_status === "pending" && canReview && (
            <div className="flex gap-2 pt-2 border-t border-slate-600/30">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onReview(anomaly.id, "confirmed");
                }}
                className="bg-verified/20 text-verified px-3 py-1.5 rounded text-xs font-medium hover:bg-verified/30 transition-colors"
              >
                ✓ Confirm
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onReview(anomaly.id, "dismissed");
                }}
                className="bg-fog-200/10 text-fog-200/60 px-3 py-1.5 rounded text-xs font-medium hover:bg-fog-200/15 transition-colors"
              >
                ✕ Dismiss
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
