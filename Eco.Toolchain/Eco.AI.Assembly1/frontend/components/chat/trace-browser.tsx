"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertCircle, Copy, FileJson, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SessionInfo, SessionTraceInfo } from "./types";
import { StatusDot } from "./project-panel";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";

interface TraceBrowserProps {
  // The project's sessions (most recent first) — the left rail of the modal.
  sessions: SessionInfo[];
  // Session the modal was opened on.
  initialSessionId: string | null;
  // Copy a trace file / dir path to the clipboard.
  onCopyPath: (path: string) => void;
  onClose: () => void;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(n < 10 * 1024 ? 1 : 0)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

// Trace Browser modal (UI_PRD I-12): sessions of the active project on the
// left, the selected session's per-call trace files on the right, and an
// auto-populated "most recent failure" footer. Row clicks copy the on-disk
// path. Driven entirely by GET /api/sessions/{id}/trace — no new backend.
export function TraceBrowser({
  sessions,
  initialSessionId,
  onCopyPath,
  onClose,
}: TraceBrowserProps) {
  const [selectedId, setSelectedId] = useState<string | null>(initialSessionId);
  const [trace, setTrace] = useState<SessionTraceInfo | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const loadTrace = useCallback(async (sessionId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/sessions/${sessionId}/trace`);
      if (res.ok) setTrace((await res.json()) as SessionTraceInfo);
      else setTrace(null);
    } catch {
      setTrace(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedId) void loadTrace(selectedId);
  }, [selectedId, loadTrace]);

  // Most recent failure = the newest recorded file carrying a non-empty
  // meta.error (files arrive oldest → newest).
  const lastFailure = trace?.files
    ? [...trace.files].reverse().find((f) => f.error)
    : undefined;
  const selectedSession = sessions.find((s) => s.id === selectedId) ?? null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, y: 12 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 12 }}
        transition={{ type: "spring", damping: 26, stiffness: 320 }}
        className="flex max-h-[85vh] w-full max-w-[min(64rem,94vw)] flex-col rounded-2xl border border-white/[0.08] glass-strong shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        {/* Title bar */}
        <div className="flex items-center justify-between px-5 pt-4 pb-3">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold">Trace Browser</h2>
            {selectedSession && (
              <p className="mt-0.5 truncate text-[11px] text-muted-foreground/70">
                {selectedSession.title || "(untitled)"} ·{" "}
                <span className="font-mono">ses-{selectedSession.id}</span> ·{" "}
                {selectedSession.status}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-foreground"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex min-h-0 flex-1 gap-3 px-5 pb-3">
          {/* Session rail */}
          <div className="w-56 shrink-0 overflow-y-auto rounded-xl border border-white/[0.06] bg-white/[0.02] thin-scroll">
            {sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                onClick={() => setSelectedId(session.id)}
                className={cn(
                  "flex w-full items-center gap-2 px-3 py-2 text-left text-[11px] transition-colors",
                  session.id === selectedId
                    ? "bg-blue-500/10 text-foreground"
                    : "text-foreground/70 hover:bg-white/[0.05]",
                )}
              >
                <StatusDot status={session.status} />
                <span className="min-w-0 flex-1 truncate">
                  {session.title || "(untitled)"}
                </span>
                <span className="shrink-0 font-mono text-[9px] text-muted-foreground/50">
                  ses-{session.id}
                </span>
              </button>
            ))}
          </div>

          {/* Trace files of the selected session */}
          <div className="min-w-0 flex-1 overflow-y-auto rounded-xl border border-white/[0.06] bg-white/[0.02] thin-scroll">
            {loading ? (
              <div className="flex h-32 items-center justify-center text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : !trace || trace.files.length === 0 ? (
              <p className="p-6 text-center text-xs text-muted-foreground/60">
                No trace files recorded for this session.
              </p>
            ) : (
              trace.files.map((file) => (
                <button
                  key={file.path}
                  type="button"
                  onClick={() => onCopyPath(file.path)}
                  title={`Click to copy: ${file.path}`}
                  className={cn(
                    "flex w-full items-center gap-2.5 px-4 py-2 text-left text-xs transition-colors hover:bg-white/[0.05]",
                    file.error && "bg-red-500/[0.05] hover:bg-red-500/[0.09]",
                  )}
                >
                  <FileJson
                    className={cn(
                      "h-3.5 w-3.5 shrink-0",
                      file.error ? "text-red-400/90" : "text-blue-300/80",
                    )}
                  />
                  <span className="min-w-0 flex-1 truncate font-mono">
                    {file.name}
                  </span>
                  {file.label && (
                    <span className="shrink-0 text-[10px] text-muted-foreground/60">
                      {file.label}
                    </span>
                  )}
                  {file.error ? (
                    <span className="shrink-0 text-[10px] font-medium text-red-300">
                      error
                    </span>
                  ) : (
                    <span className="shrink-0 text-[10px] text-emerald-300/80">
                      ok
                    </span>
                  )}
                  <span className="shrink-0 font-mono text-[10px] text-muted-foreground/50">
                    {formatBytes(file.size)}
                  </span>
                  <Copy className="h-3 w-3 shrink-0 text-muted-foreground/40" />
                </button>
              ))
            )}
          </div>
        </div>

        {/* Most recent failure */}
        {lastFailure && (
          <div className="mx-5 mb-4 rounded-xl border border-red-500/25 bg-red-500/[0.06] px-3 py-2">
            <div className="flex items-center gap-2 text-[11px] font-medium text-red-300">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              Most recent failure
              <span className="truncate font-mono font-normal text-red-300/70">
                {lastFailure.name}
              </span>
              <button
                type="button"
                onClick={() => onCopyPath(lastFailure.path)}
                className="ml-auto shrink-0 rounded p-0.5 text-red-300/70 transition-colors hover:bg-red-500/10 hover:text-red-200"
                title={`Copy path: ${lastFailure.path}`}
                aria-label="Copy failing trace path"
              >
                <Copy className="h-3 w-3" />
              </button>
            </div>
            <p className="mt-1 break-words font-mono text-[10px] leading-relaxed text-red-200/80">
              {lastFailure.error}
            </p>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
