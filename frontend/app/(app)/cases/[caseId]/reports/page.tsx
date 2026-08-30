"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

type Report = {
  id: string;
  case_id: string;
  format: string;
  status: string;
  title: string;
  content_hash: string;
  created_by: string;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
};

const FORMAT_OPTIONS = [
  { value: "pdf", label: "PDF Report", desc: "Formatted investigation report with tables and charts" },
  { value: "csv", label: "CSV Export", desc: "Raw event data for spreadsheet analysis" },
  { value: "json", label: "JSON Export", desc: "Machine-readable format for SIEM/SOAR integration" },
  { value: "text", label: "Text Report", desc: "Plain text report for easy review" },
];

export default function ReportsPage({
  params,
}: {
  params: { caseId: string };
}) {
  const queryClient = useQueryClient();
  const [selectedFormat, setSelectedFormat] = useState("pdf");
  const [customTitle, setCustomTitle] = useState("");
  const [showGenerateForm, setShowGenerateForm] = useState(false);

  const reportsQuery = useQuery<Report[], Error>({
    queryKey: ["reports", params.caseId],
    queryFn: () => api.reports.list(params.caseId),
  });

  const generateMutation = useMutation({
    mutationFn: (format: string) =>
      api.reports.generate(params.caseId, {
        format,
        title: customTitle || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports", params.caseId] });
      setShowGenerateForm(false);
      setCustomTitle("");
    },
  });

  const approveMutation = useMutation({
    mutationFn: (reportId: string) =>
      api.reports.approve(params.caseId, reportId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports", params.caseId] });
    },
  });

  const reports: Report[] = reportsQuery.data ?? [];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="font-display text-xl font-semibold">Reports</h1>
        <p className="text-sm text-fog-200/50 mt-1">
          Generate and export investigation reports with tamper-evident hashing.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {FORMAT_OPTIONS.map((fmt) => (
          <button
            key={fmt.value}
            onClick={() => {
              setSelectedFormat(fmt.value);
              setShowGenerateForm(true);
            }}
            className="bg-slate-800 border border-slate-600 rounded-lg p-4 text-left hover:border-trace-cyan/50 transition-colors"
          >
            <div className="text-sm font-medium text-fog-200 mb-1">{fmt.label}</div>
            <div className="text-xs text-fog-200/50">{fmt.desc}</div>
          </button>
        ))}
      </div>

      {showGenerateForm && (
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-medium text-fog-200 mb-3">
            Generate {FORMAT_OPTIONS.find((f) => f.value === selectedFormat)?.label}
          </h3>
          <div className="mb-3">
            <label className="block text-xs font-medium uppercase tracking-wider mb-1">
              Custom Title (optional)
            </label>
            <input
              type="text"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
              placeholder="Leave blank for default title"
              className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 text-sm focus:outline-none focus:ring-2 focus:ring-trace-cyan"
            />
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => generateMutation.mutate(selectedFormat)}
              disabled={generateMutation.isPending}
              className="bg-trace-cyan text-ink-950 px-6 py-2 rounded text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {generateMutation.isPending ? "Generating..." : "Generate Report"}
            </button>
            <button
              onClick={() => {
                setShowGenerateForm(false);
                setCustomTitle("");
              }}
              className="bg-slate-600 text-fog-200 px-4 py-2 rounded text-sm hover:opacity-80"
            >
              Cancel
            </button>
          </div>
          {generateMutation.error && (
            <p className="text-red-400 text-xs mt-2">
              {generateMutation.error.message}
            </p>
          )}
        </div>
      )}

      {reportsQuery.isLoading ? (
        <div className="text-fog-200/40 text-sm">Loading reports...</div>
      ) : reports.length === 0 ? (
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-8 text-center">
          <p className="text-fog-200/40 text-sm">
            No reports generated yet. Select a format above to create your first report.
          </p>
        </div>
      ) : (
        <div className="bg-slate-800 border border-slate-600 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-600 text-xs font-medium uppercase tracking-wider text-fog-200/60">
                <th className="px-4 py-3 text-left">Title</th>
                <th className="px-4 py-3 text-left">Format</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Content Hash (SHA-256)</th>
                <th className="px-4 py-3 text-left">Created</th>
                <th className="px-4 py-3 text-left">Approved</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report, idx) => (
                <tr
                  key={report.id}
                  className={`border-b border-slate-600/50 ${
                    idx % 2 === 1 ? "bg-fog-200/[0.04]" : ""
                  }`}
                >
                  <td className="px-4 py-3 font-medium text-fog-200 max-w-[200px] truncate">
                    {report.title}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-block bg-slate-600/50 text-fog-200/80 px-2 py-0.5 rounded text-xs font-mono uppercase">
                      {report.format}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {report.status === "approved" ? (
                      <span className="inline-block bg-green-900/30 text-green-400 px-2 py-0.5 rounded text-xs">
                        Approved
                      </span>
                    ) : (
                      <span className="inline-block bg-yellow-900/30 text-yellow-400 px-2 py-0.5 rounded text-xs">
                        Draft
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-trace-cyan/70 max-w-[180px] truncate" title={report.content_hash}>
                    {report.content_hash}
                  </td>
                  <td className="px-4 py-3 text-xs text-fog-200/50">
                    {new Date(report.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-xs text-fog-200/50">
                    {report.approved_at
                      ? new Date(report.approved_at).toLocaleString()
                      : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <a
                        href={api.reports.downloadUrl(params.caseId, report.id)}
                        className="text-xs text-trace-cyan hover:underline"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Download
                      </a>
                      {report.status === "draft" && (
                        <button
                          onClick={() => approveMutation.mutate(report.id)}
                          disabled={approveMutation.isPending}
                          className="text-xs text-green-400 hover:underline disabled:opacity-50"
                        >
                          Approve
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
