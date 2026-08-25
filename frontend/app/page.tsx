"use client";

import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="text-center max-w-lg">
        <h1 className="font-display text-4xl font-bold mb-3">
          Cyber Forensics Platform
        </h1>
        <p className="text-fog-200/60 text-lg mb-8">
          AI-Based Log Investigation Framework for Digital Forensics
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/cases"
            className="bg-trace-cyan text-ink-950 px-6 py-3 rounded-lg font-medium hover:opacity-90 transition-opacity"
          >
            Open Dashboard
          </Link>
          <Link
            href="/(auth)/login"
            className="bg-slate-800 border border-slate-600 text-fog-200 px-6 py-3 rounded-lg font-medium hover:border-trace-cyan/30 transition-colors"
          >
            Sign In
          </Link>
        </div>
      </div>
    </main>
  );
}
