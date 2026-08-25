"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isRegister) {
        const res = await fetch(`${API_URL}/api/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, email, password, role: "investigator" }),
        });
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || "Registration failed");
        }
      }

      const loginRes = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!loginRes.ok) {
        const data = await loginRes.json();
        throw new Error(data.detail || "Login failed");
      }

      const { access_token } = await loginRes.json();
      localStorage.setItem("token", access_token);
      router.push("/cases");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md bg-slate-800 border border-slate-600 rounded-lg p-8">
        <h1 className="font-display text-2xl font-semibold text-center mb-6">
          {isRegister ? "Create Account" : "Sign In"}
        </h1>

        {error && (
          <div className="bg-critical/10 border border-critical text-critical px-4 py-2 rounded mb-4 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider mb-1">
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 focus:outline-none focus:ring-2 focus:ring-trace-cyan"
              required
            />
          </div>

          {isRegister && (
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 focus:outline-none focus:ring-2 focus:ring-trace-cyan"
                required
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium uppercase tracking-wider mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-ink-950 border border-slate-600 rounded px-3 py-2 text-fog-200 focus:outline-none focus:ring-2 focus:ring-trace-cyan"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-trace-cyan text-ink-950 py-2 rounded font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? "Please wait..." : isRegister ? "Register" : "Sign In"}
          </button>
        </form>

        <p className="text-center text-sm text-fog-200/60 mt-4">
          {isRegister ? "Already have an account?" : "Don't have an account?"}{" "}
          <button
            onClick={() => setIsRegister(!isRegister)}
            className="text-trace-cyan hover:underline"
          >
            {isRegister ? "Sign In" : "Register"}
          </button>
        </p>
      </div>
    </main>
  );
}
