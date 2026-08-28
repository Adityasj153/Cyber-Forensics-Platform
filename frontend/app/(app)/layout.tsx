"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import Sidebar from "@/components/sidebar";

const ROLE_COLORS: Record<string, string> = {
  admin: "text-critical border-critical",
  investigator: "text-evidence-amber border-evidence-amber",
  viewer: "text-trace-cyan border-trace-cyan",
};

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  const user = session?.user as any;
  const role: string = user?.role ?? "";
  const roleColor = ROLE_COLORS[role] ?? "text-fog-200 border-fog-200";

  const handleLogout = async () => {
    setSigningOut(true);
    await signOut({ redirect: false, callbackUrl: "/login" });
    router.push("/login");
  };

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between px-6 h-16 border-b border-slate-600 bg-slate-800 shrink-0">
        <Link href="/cases" className="flex items-center gap-3">
          <span className="h-2.5 w-2.5 rounded-full bg-trace-cyan shrink-0" />
          <span className="font-display font-semibold text-lg tracking-wide">
            Cyber Forensics Platform
          </span>
        </Link>

        {status === "authenticated" && user ? (
          <div className="flex items-center gap-4">
            <span className="text-sm text-fog-200/80">{user.name}</span>
            {role && (
              <span
                className={`text-xs font-medium uppercase tracking-wider border px-2.5 py-1 rounded ${roleColor}`}
              >
                {role}
              </span>
            )}
            <button
              onClick={handleLogout}
              disabled={signingOut}
              className="text-xs text-fog-200/70 hover:text-fog-200 hover:bg-slate-600/40 px-3 py-1.5 rounded transition-colors disabled:opacity-50"
            >
              {signingOut ? "Signing out..." : "Logout"}
            </button>
          </div>
        ) : (
          <div className="text-xs text-fog-200/50">Not signed in</div>
        )}
      </header>

      <div className="flex flex-1 min-h-0">
        <aside className="w-56 border-r border-slate-600 bg-slate-800 flex flex-col shrink-0">
          <Sidebar />
        </aside>
        <main className="flex-1 min-w-0 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
