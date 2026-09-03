"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { KeyRound, Loader2, ShieldCheck, SkipForward } from "lucide-react";
import { API_URL } from "@/lib/api";

type SetupStatus = {
  configured: boolean;
  items: Record<string, { label: string; required: boolean; configured: boolean; masked: string | null }>;
  env_file: string;
};

export default function SetupPage() {
  const router = useRouter();
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [key, setKey] = useState("");
  const [ecoToken, setEcoToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/setup/status`)
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  async function save() {
    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/api/setup/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ openrouter_key: key, eco_token: ecoToken }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Setup failed");
      setSaved(true);
      setTimeout(() => router.push("/"), 800);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function skip() {
    // "Add later in .env" — missing keys never block the app.
    router.push("/");
  }

  return (
    <main className="min-h-screen bg-background flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md rounded-xl border border-border bg-card p-8 shadow-lg space-y-6"
      >
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-primary/10 p-2">
            <KeyRound className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">Finish setup</h1>
            <p className="text-sm text-muted-foreground">
              Configure your harness — or skip and add keys later.
            </p>
          </div>
        </div>

        {saved ? (
          <div className="flex items-center gap-2 rounded-lg border border-green-500/30 bg-green-500/10 p-3 text-sm text-green-500">
            <ShieldCheck className="h-4 w-4" /> Saved. Opening the app…
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="or-key">
                OpenRouter API key <span className="text-red-500">*</span>
              </label>
              <input
                id="or-key"
                type="password"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder="sk-or-v1-…"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
              />
              {status?.items.openrouter_key.configured && (
                <p className="text-xs text-muted-foreground">
                  Currently set ({status.items.openrouter_key.masked}) — leave blank to keep.
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="eco-token">
                EcoOS marketplace token <span className="text-muted-foreground">(optional)</span>
              </label>
              <input
                id="eco-token"
                type="password"
                value={ecoToken}
                onChange={(e) => setEcoToken(e.target.value)}
                placeholder="ecoos.dev marketplace token"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            {error && (
              <p className="rounded-md border border-red-500/30 bg-red-500/10 p-2 text-sm text-red-500">
                {error}
              </p>
            )}

            <div className="flex flex-col gap-2">
              <button
                onClick={save}
                disabled={busy || (!key && !ecoToken)}
                className="flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                Validate &amp; save
              </button>
              <button
                onClick={skip}
                className="flex items-center justify-center gap-2 rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted"
              >
                <SkipForward className="h-4 w-4" />
                Skip — add later in .env
              </button>
            </div>

            <p className="text-xs text-muted-foreground">
              Keys are written to <code className="font-mono">{status?.env_file || "~/.eco-harness/.env"}</code>.
              Environment variables already set always take precedence.
            </p>
          </div>
        )}
      </motion.div>
    </main>
  );
}
