"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

const SECTION_NAV = [
  { label: "Overview", href: "" },
  { label: "Timeline", href: "/timeline" },
  { label: "Correlation", href: "/correlation" },
  { label: "Anomalies", href: "/anomalies" },
  { label: "Search", href: "/search" },
  { label: "NL Query", href: "/nl-query" },
  { label: "Reports", href: "/reports" },
];

function useCaseRoute(): { caseId: string | null } {
  const pathname = usePathname();
  const m = pathname.match(/^\/cases\/([^/]+)/);
  return { caseId: m ? m[1] : null };
}

export default function Sidebar() {
  const pathname = usePathname();
  const { caseId } = useCaseRoute();

  const caseQuery = useQuery({
    queryKey: ["case", caseId ?? "__none__"],
    queryFn: () => api.cases.get(caseId as string),
    enabled: !!caseId,
  });

  const caseData = caseQuery.data ?? null;
  const casesListActive = pathname === "/cases";

  return (
    <nav className="flex-1 p-2 flex flex-col gap-1">
      <Link
        href="/cases"
        className={`block px-3 py-2 rounded text-sm transition-colors ${
          casesListActive
            ? "bg-trace-cyan/10 text-trace-cyan"
            : "text-fog-200/70 hover:text-fog-200 hover:bg-fog-200/5"
        }`}
      >
        All Cases
      </Link>

      {caseId && (
        <>
          <div className="mt-4 px-3">
            <Link
              href={`/cases/${caseId}`}
              className="font-display text-sm font-semibold text-fog-200 truncate hover:text-trace-cyan transition-colors"
              title={caseData?.name}
            >
              {caseData?.name || "Case"}
            </Link>
            <div className="text-xs text-fog-200/40 font-mono truncate mt-0.5">
              {caseId.slice(0, 8)}...
            </div>
          </div>

          <div className="mt-3 space-y-0.5">
            {SECTION_NAV.map((item) => {
              const href =
                item.href === ""
                  ? `/cases/${caseId}`
                  : `/cases/${caseId}${item.href}`;
              const isActive =
                item.href === "" ? pathname === href : pathname.startsWith(href);
              return (
                <Link
                  key={item.href || "overview"}
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
          </div>
        </>
      )}
    </nav>
  );
}
