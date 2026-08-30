"use client";

export default function NLQueryPage({
  params,
}: {
  params: { caseId: string };
}) {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="font-display text-xl font-semibold">Natural Language Query</h1>
        <p className="text-sm text-fog-200/50 mt-1">
          Ask questions about this case in plain English.
        </p>
      </div>
      <div className="bg-slate-800 border border-slate-600 rounded-lg p-8 text-center">
        <p className="text-fog-200/40">
          Natural language query powered by AI is coming in Phase 4.
        </p>
      </div>
    </div>
  );
}
