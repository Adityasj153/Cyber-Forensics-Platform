"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { api, Case } from "@/lib/api-client";

export default function CasesPage() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/(auth)/login");
      return;
    }
    if (status === "authenticated") {
      api.cases
        .list()
        .then(setCases)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [status, router]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const c = await api.cases.create({ name: newName, description: newDesc || undefined });
      setCases((prev) => [c, ...prev]);
      setShowCreate(false);
      setNewName("");
      setNewDesc("");
    } catch (err) {
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "open":
        return "text-trace-cyan";
      case "in_progress":
        return "text-evidence-amber";
      case "closed":
        return "text-fog-200/50";
      default:
        return "text-fog-200";
    }
  };

  return (
    <main className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="font-display text-2xl font-semibold">Cases</h1>
          <button
            onClick={() => setShowCreate(true)}
            className="bg-trace-cyan text-ink-950 px-4 py-2 rounded text-sm font-medium hover:opacity-90 transition-opacity"
          >
            + New Case
          </button>
        </div>

        {showCreate && (
          <form
            onSubmit={handleCreate}
            className="bg-slate-800 border border-slate-600 rounded-lg p-4 mb-6"
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium uppercase tracking-wider mb-1">
                  Case Name
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g., Insider Exfiltration Investigation"
                  className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 text-sm focus:outline-none focus:ring-2 focus:ring-trace-cyan"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-medium uppercase tracking-wider mb-1">
                  Description
                </label>
                <input
                  type="text"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Optional description"
                  className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 text-sm focus:outline-none focus:ring-2 focus:ring-trace-cyan"
                />
              </div>
              <div className="flex items-end gap-2">
                <button
                  type="submit"
                  disabled={creating || !newName.trim()}
                  className="bg-trace-cyan text-ink-950 px-4 py-2 rounded text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Create"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="bg-slate-600 text-fog-200 px-4 py-2 rounded text-sm hover:opacity-80"
                >
                  Cancel
                </button>
              </div>
            </div>
          </form>
        )}

        {loading ? (
          <div className="text-center py-12 text-fog-200/40">Loading cases...</div>
        ) : cases.length === 0 ? (
          <div className="bg-slate-800 border border-slate-600 rounded-lg p-8 text-center">
            <p className="text-fog-200/60">
              No cases yet. Create your first investigation case to get started.
            </p>
          </div>
        ) : (
          <div className="grid gap-3">
            {cases.map((c) => (
              <Link
                key={c.id}
                href={`/cases/${c.id}`}
                className="block bg-slate-800 border border-slate-600 rounded-lg p-4 hover:border-trace-cyan/30 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="min-w-0">
                    <div className="font-medium text-fog-200 truncate">
                      {c.name}
                    </div>
                    {c.description && (
                      <div className="text-sm text-fog-200/50 mt-1 truncate">
                        {c.description}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-4 ml-4 shrink-0">
                    <span className={`text-xs font-medium uppercase ${statusColor(c.status)}`}>
                      {c.status.replace("_", " ")}
                    </span>
                    <span className="text-xs text-fog-200/40">
                      {new Date(c.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
