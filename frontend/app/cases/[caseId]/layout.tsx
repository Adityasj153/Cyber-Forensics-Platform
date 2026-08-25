"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { label: "Overview", href: "" },
  { label: "Timeline", href: "/timeline" },
  { label: "Correlation", href: "/correlation" },
  { label: "Anomalies", href: "/anomalies" },
  { label: "Search", href: "/search" },
  { label: "Reports", href: "/reports" },
];

export default function CaseLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { caseId: string };
}) {
  const pathname = usePathname();
  const basePath = `/cases/${params.caseId}`;

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 bg-slate-800 border-r border-slate-600 flex flex-col shrink-0">
        <div className="p-4 border-b border-slate-600">
          <Link
            href="/cases"
            className="text-xs text-fog-200/50 hover:text-fog-200 transition-colors"
          >
            &larr; All Cases
          </Link>
          <div className="font-display text-sm font-semibold mt-2 truncate">
            Case
          </div>
          <div className="text-xs text-fog-200/40 font-mono truncate">
            {params.caseId.slice(0, 8)}...
          </div>
        </div>
        <nav className="flex-1 p-2">
          {NAV_ITEMS.map((item) => {
            const href = `${basePath}${item.href}`;
            const isActive =
              item.href === ""
                ? pathname === basePath
                : pathname.startsWith(href);
            return (
              <Link
                key={item.href}
                href={href}
                className={`block px-3 py-2 rounded text-sm transition-colors ${
                  isActive
                    ? "bg-trace-cyan/10 text-trace-cyan"
                    : "text-fog-200/60 hover:text-fog-200 hover:bg-fog-200/5"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  );
}
