"use client";

export default function ReportsPage({
  params,
}: {
  params: { caseId: string };
}) {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="font-display text-xl font-semibold">Reports</h1>
        <p className="text-sm text-fog-200/50 mt-1">
          Generate and export investigation reports. Coming in Phase 4.
        </p>
      </div>

      <div className="bg-slate-800 border border-slate-600 rounded-lg p-8 text-center">
        <div className="text-4xl mb-4">◫</div>
        <h2 className="font-display text-lg font-semibold mb-2">
          Reporting Engine
        </h2>
        <p className="text-fog-200/60 text-sm max-w-md mx-auto mb-4">
          PDF, CSV, and JSON export with tamper-evident hashing will be available here.
          Reports will include case metadata, timeline, entities, AI findings, and investigator sign-off.
        </p>
        <div className="inline-block bg-slate-600/30 text-fog-200/50 px-4 py-2 rounded text-xs">
          Phase 4 — Coming Soon
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          {
            format: "PDF Report",
            desc: "Formatted investigation report with timeline, entities, and AI findings",
            status: "Planned",
          },
          {
            format: "CSV Export",
            desc: "Raw and normalized event data for spreadsheet analysis",
            status: "Planned",
          },
          {
            format: "JSON Export",
            desc: "Machine-readable format for SIEM/SOAR integration",
            status: "Planned",
          },
        ].map((item) => (
          <div
            key={item.format}
            className="bg-slate-800 border border-slate-600/50 rounded-lg p-4"
          >
            <div className="text-sm font-medium text-fog-200 mb-1">
              {item.format}
            </div>
            <div className="text-xs text-fog-200/50 mb-2">{item.desc}</div>
            <span className="text-xs bg-slate-600/30 text-fog-200/40 px-2 py-0.5 rounded">
              {item.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
