"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

interface NLResult {
  answer: string;
  cited_event_ids: string[];
  filters_applied: {
    source_type: string | null;
    action: string | null;
    device_id: string | null;
    ip_address: string | null;
    timestamp_from: string | null;
    timestamp_to: string | null;
    query: string | null;
    offset: number;
    size: number;
  };
  total_found: number;
}

export default function NLQueryPage({
  params,
}: {
  params: { caseId: string };
}) {
  const [question, setQuestion] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState("");

  const nlQuery = useQuery<NLResult, Error>({
    queryKey: ["nl-query", params.caseId, submittedQuestion],
    queryFn: () => api.nlQuery.query(params.caseId, submittedQuestion),
    enabled: submittedQuestion.length > 0,
    retry: false,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setSubmittedQuestion(question.trim());
  };

  const result = nlQuery.data;
  const loading = nlQuery.isFetching;
  const error = nlQuery.error;

  const activeFilters = result?.filters_applied
    ? Object.entries(result.filters_applied).filter(([k, v]) =>
        v !== null && v !== undefined && v !== "" && !["offset", "size"].includes(k),
      )
    : [];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="font-display text-xl font-semibold">Natural Language Query</h1>
        <p className="text-sm text-fog-200/50 mt-1">
          Ask questions about this case in plain English.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="bg-slate-800 border border-slate-600 rounded-lg p-4 mb-6"
      >
        <label className="block text-xs font-medium uppercase tracking-wider mb-2">
          Your Question
        </label>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What did jsmith do with Q3_financials.xlsx? or Show me all USB transfer activity last week"
          rows={3}
          className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-trace-cyan resize-y mb-3"
        />
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="bg-trace-cyan text-ink-950 px-6 py-2 rounded text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? "Querying..." : "Ask"}
          </button>
          {submittedQuestion && (
            <span className="text-xs text-fog-200/40 italic truncate max-w-md">
              &ldquo;{submittedQuestion}&rdquo;
            </span>
          )}
        </div>
      </form>

      {error && (
        <div className="bg-red-900/20 border border-red-700/40 rounded-lg p-4 mb-6">
          <p className="text-red-400 text-sm font-medium">Query failed</p>
          <p className="text-red-400/70 text-xs mt-1">{error.message}</p>
        </div>
      )}

      {result && (
        <>
          <div className="mb-4 flex items-center gap-4 text-sm text-fog-200/50">
            <span>{result.total_found} event{result.total_found !== 1 ? "s" : ""} found</span>
            {activeFilters.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {activeFilters.map(([k, v]) => (
                  <span
                    key={k}
                    className="inline-block bg-slate-600/50 text-fog-200/80 px-2 py-0.5 rounded text-xs font-mono"
                  >
                    {k}: {String(v)}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="bg-slate-800 border border-slate-600 rounded-lg p-4 mb-4">
            <p className="text-fog-200 text-sm leading-relaxed whitespace-pre-wrap">
              {result.answer}
            </p>
          </div>

          {result.cited_event_ids.length > 0 && (
            <div className="bg-slate-800 border border-slate-600 rounded-lg p-4">
              <p className="text-xs font-medium uppercase tracking-wider text-fog-200/60 mb-3">
                Cited Event IDs ({result.cited_event_ids.length})
              </p>
              <div className="flex flex-wrap gap-2">
                {result.cited_event_ids.map((id) => (
                  <span
                    key={id}
                    className="inline-block bg-ink-950 border border-slate-600 text-trace-cyan/80 px-2 py-1 rounded font-mono text-xs"
                    title={id}
                  >
                    {id}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {!result && !loading && !error && (
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-8 text-center">
          <p className="text-fog-200/40 text-sm">
            Ask a question above to search the case event log.
          </p>
        </div>
      )}
    </div>
  );
}
