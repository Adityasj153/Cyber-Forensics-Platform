"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { api, Case, Device, Artifact } from "@/lib/api-client";

export default function CaseOverviewPage({
  params,
}: {
  params: { caseId: string };
}) {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddDevice, setShowAddDevice] = useState(false);
  const [deviceForm, setDeviceForm] = useState({
    device_type: "pc",
    os: "",
    owner: "",
    name: "",
  });
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
      return;
    }
    if (status !== "authenticated") return;
    Promise.all([
      api.cases.get(params.caseId),
      api.devices.list(params.caseId).catch(() => []),
      api.artifacts.list(params.caseId).catch(() => []),
    ])
      .then(([c, d, a]) => {
        setCaseData(c);
        setDevices(d);
        setArtifacts(a);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [params.caseId, status, router]);

  const handleAddDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const dev = await api.devices.create(params.caseId, {
        device_type: deviceForm.device_type,
        os: deviceForm.os || undefined,
        owner: deviceForm.owner || undefined,
        name: deviceForm.name || undefined,
      });
      setDevices((prev) => [...prev, dev]);
      setShowAddDevice(false);
      setDeviceForm({ device_type: "pc", os: "", owner: "", name: "" });
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const artifact = await api.artifacts.upload(params.caseId, file);
      setArtifacts((prev) => [artifact, ...prev]);
    } catch (err) {
      console.error(err);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "parsed":
        return "text-verified";
      case "queued":
      case "parsing":
        return "text-evidence-amber";
      case "parse_failed":
        return "text-critical";
      default:
        return "text-fog-200/60";
    }
  };

  if (loading) {
    return (
      <div className="p-6 text-center text-fog-200/40">Loading case...</div>
    );
  }

  if (!caseData) {
    return (
      <div className="p-6 text-center text-critical">Case not found.</div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold">{caseData.name}</h1>
        {caseData.description && (
          <p className="text-fog-200/50 text-sm mt-1">{caseData.description}</p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-fog-200/60 mb-1">
            Status
          </div>
          <div className="text-trace-cyan font-medium capitalize">
            {caseData.status.replace("_", " ")}
          </div>
        </div>
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-fog-200/60 mb-1">
            Devices
          </div>
          <div className="text-fog-200 font-medium">{devices.length}</div>
        </div>
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-fog-200/60 mb-1">
            Artifacts
          </div>
          <div className="text-fog-200 font-medium">{artifacts.length}</div>
        </div>
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-fog-200/60 mb-1">
            Created
          </div>
          <div className="text-fog-200 font-medium text-sm">
            {new Date(caseData.created_at).toLocaleDateString()}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Devices */}
        <div className="bg-slate-800 border border-slate-600 rounded-lg">
          <div className="flex items-center justify-between p-4 border-b border-slate-600">
            <h2 className="font-display text-sm font-semibold">Devices</h2>
            <button
              onClick={() => setShowAddDevice(true)}
              className="text-xs text-trace-cyan hover:opacity-80"
            >
              + Add Device
            </button>
          </div>
          {showAddDevice && (
            <form
              onSubmit={handleAddDevice}
              className="p-4 border-b border-slate-600 bg-ink-950/50"
            >
              <div className="grid grid-cols-2 gap-3">
                <select
                  value={deviceForm.device_type}
                  onChange={(e) =>
                    setDeviceForm((p) => ({ ...p, device_type: e.target.value }))
                  }
                  className="bg-ink-950 border border-slate-600 rounded px-3 py-1.5 text-sm text-fog-200"
                >
                  <option value="pc">PC</option>
                  <option value="mobile">Mobile</option>
                  <option value="server">Server</option>
                  <option value="network">Network</option>
                </select>
                <input
                  type="text"
                  placeholder="Name"
                  value={deviceForm.name}
                  onChange={(e) =>
                    setDeviceForm((p) => ({ ...p, name: e.target.value }))
                  }
                  className="bg-ink-950 border border-slate-600 rounded px-3 py-1.5 text-sm text-fog-200"
                />
                <input
                  type="text"
                  placeholder="OS"
                  value={deviceForm.os}
                  onChange={(e) =>
                    setDeviceForm((p) => ({ ...p, os: e.target.value }))
                  }
                  className="bg-ink-950 border border-slate-600 rounded px-3 py-1.5 text-sm text-fog-200"
                />
                <input
                  type="text"
                  placeholder="Owner"
                  value={deviceForm.owner}
                  onChange={(e) =>
                    setDeviceForm((p) => ({ ...p, owner: e.target.value }))
                  }
                  className="bg-ink-950 border border-slate-600 rounded px-3 py-1.5 text-sm text-fog-200"
                />
              </div>
              <div className="flex gap-2 mt-3">
                <button
                  type="submit"
                  className="bg-trace-cyan text-ink-950 px-3 py-1 rounded text-xs font-medium"
                >
                  Add
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddDevice(false)}
                  className="text-fog-200/60 text-xs"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
          <div className="p-4">
            {devices.length === 0 ? (
              <p className="text-fog-200/40 text-sm text-center py-4">
                No devices added yet.
              </p>
            ) : (
              <div className="space-y-2">
                {devices.map((d) => (
                  <div
                    key={d.id}
                    className="flex items-center justify-between bg-ink-950/50 rounded px-3 py-2"
                  >
                    <div>
                      <span className="text-sm font-medium text-fog-200">
                        {d.name || d.device_type}
                      </span>
                      <span className="text-xs text-fog-200/40 ml-2 uppercase">
                        {d.device_type}
                      </span>
                    </div>
                    <div className="text-xs text-fog-200/40">
                      {d.os && <span>{d.os}</span>}
                      {d.owner && <span className="ml-2">· {d.owner}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Artifacts */}
        <div className="bg-slate-800 border border-slate-600 rounded-lg">
          <div className="flex items-center justify-between p-4 border-b border-slate-600">
            <h2 className="font-display text-sm font-semibold">Artifacts</h2>
            <label className="text-xs text-trace-cyan hover:opacity-80 cursor-pointer">
              {uploading ? "Uploading..." : "+ Upload File"}
              <input
                type="file"
                className="hidden"
                onChange={handleUpload}
                disabled={uploading}
              />
            </label>
          </div>
          <div className="p-4">
            {artifacts.length === 0 ? (
              <p className="text-fog-200/40 text-sm text-center py-4">
                No artifacts uploaded yet. Upload log files to begin analysis.
              </p>
            ) : (
              <div className="space-y-2">
                {artifacts.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-center justify-between bg-ink-950/50 rounded px-3 py-2"
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-mono text-fog-200 truncate">
                        {a.filename}
                      </div>
                      <div className="text-xs text-fog-200/40 font-mono">
                        {a.sha256.slice(0, 16)}...
                      </div>
                    </div>
                    <span
                      className={`text-xs font-medium uppercase ml-3 shrink-0 ${statusColor(
                        a.status
                      )}`}
                    >
                      {a.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Links */}
      <div className="mt-6 grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: "Timeline", href: "timeline", icon: "→" },
          { label: "Correlation", href: "correlation", icon: "⊛" },
          { label: "Anomalies", href: "anomalies", icon: "⚠" },
          { label: "Search", href: "search", icon: "⌕" },
          { label: "Reports", href: "reports", icon: "◫" },
        ].map((item) => (
          <Link
            key={item.href}
            href={`/cases/${params.caseId}/${item.href}`}
            className="bg-slate-800 border border-slate-600 rounded-lg p-3 text-center hover:border-trace-cyan/30 transition-colors"
          >
            <div className="text-lg mb-1">{item.icon}</div>
            <div className="text-xs font-medium text-fog-200/70">
              {item.label}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
