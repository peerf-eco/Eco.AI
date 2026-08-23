"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertCircle,
  ArrowUp,
  Check,
  ChevronRight,
  CornerDownLeft,
  FolderClosed,
  Loader2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { FsListing } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";

interface FolderBrowserProps {
  onClose: () => void;
  // POST /api/projects returns the bare registry entry (no sessions yet).
  onAdded: (project: { path: string; name: string; id: string }) => void;
}

// Modal folder picker backed by GET /api/fs/browse (directories only) and
// POST /api/projects to register the chosen folder. Starts in the user's
// home directory; breadcrumb segments jump back up the tree.
export function FolderBrowser({ onClose, onAdded }: FolderBrowserProps) {
  const [listing, setListing] = useState<FsListing | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pathDraft, setPathDraft] = useState("");

  const fetchListing = useCallback(async (path?: string) => {
    setLoading(true);
    setError(null);
    try {
      const qs = path ? `?path=${encodeURIComponent(path)}` : "";
      const res = await fetch(`${API_URL}/api/fs/browse${qs}`);
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Request failed (${res.status})`);
      }
      setListing((await res.json()) as FsListing);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to browse folders");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!listing && loading) void fetchListing();
  }, [listing, loading, fetchListing]);

  // Keep the editable path field in sync with wherever the user navigates.
  useEffect(() => {
    if (listing) setPathDraft(listing.path);
  }, [listing]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const selectFolder = async () => {
    if (!listing) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: listing.path }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Request failed (${res.status})`);
      }
      onAdded((await res.json()) as { path: string; name: string; id: string });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add project");
      setSubmitting(false);
    }
  };

  // "/home/nick/Dev" → ["/", "home", "nick", "Dev"] clickable crumbs.
  const crumbs: { label: string; path: string }[] = [];
  if (listing) {
    const parts = listing.path.split("/").filter(Boolean);
    crumbs.push({ label: "/", path: "/" });
    parts.forEach((part, index) => {
      crumbs.push({
        label: part,
        path: "/" + parts.slice(0, index + 1).join("/"),
      });
    });
  }

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
        className="w-full max-w-lg rounded-2xl border border-white/[0.08] glass-strong shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        {/* Title bar */}
        <div className="flex items-center justify-between px-5 pt-4 pb-3">
          <h2 className="text-sm font-semibold">Choose project folder</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-foreground"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Breadcrumb + manual path entry */}
        <div className="mx-5 mb-2 space-y-1.5">
          <div className="flex items-center gap-0.5 overflow-x-auto whitespace-nowrap rounded-lg bg-black/40 px-3 py-2 text-xs thin-scroll">
            {crumbs.map((crumb, index) => (
              <span key={crumb.path} className="flex items-center shrink-0">
                {index > 0 && <ChevronRight className="h-3 w-3 mx-0.5 text-muted-foreground/40" />}
                <button
                  type="button"
                  onClick={() => void fetchListing(crumb.path)}
                  className={cn(
                    "rounded px-1 py-0.5 font-mono transition-colors hover:bg-white/[0.08]",
                    index === crumbs.length - 1
                      ? "text-blue-300"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {crumb.label}
                </button>
              </span>
            ))}
          </div>
          <form
            className="flex items-center gap-2 rounded-lg bg-black/40 px-3 py-1.5"
            onSubmit={(event) => {
              event.preventDefault();
              if (pathDraft.trim()) void fetchListing(pathDraft.trim());
            }}
          >
            <span className="font-mono text-[10px] text-muted-foreground/50">/</span>
            <input
              value={pathDraft}
              onChange={(event) => setPathDraft(event.target.value)}
              placeholder="Type a path, e.g. /app/output…"
              spellCheck={false}
              className="w-full bg-transparent font-mono text-[11px] outline-none placeholder:text-muted-foreground/40"
            />
            <button
              type="submit"
              title="Open path"
              className="shrink-0 rounded p-1 text-muted-foreground transition-colors hover:bg-white/[0.08] hover:text-foreground"
            >
              <CornerDownLeft className="h-3 w-3" />
            </button>
          </form>
        </div>

        {/* Directory list */}
        <div className="mx-5 h-64 overflow-y-auto rounded-xl border border-white/[0.06] bg-white/[0.02] thin-scroll">
          {loading ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : (
            <>
              {listing?.parent && (
                <button
                  type="button"
                  onClick={() => void fetchListing(listing.parent as string)}
                  className="flex w-full items-center gap-2.5 px-4 py-2 text-left text-xs text-muted-foreground transition-colors hover:bg-white/[0.05]"
                >
                  <ArrowUp className="h-3.5 w-3.5" />
                  ..
                </button>
              )}
              {listing?.entries.map((entry) => (
                <button
                  key={entry.path}
                  type="button"
                  onClick={() => void fetchListing(entry.path)}
                  className="flex w-full items-center gap-2.5 px-4 py-2 text-left text-xs transition-colors hover:bg-white/[0.05]"
                >
                  <FolderClosed className="h-3.5 w-3.5 shrink-0 text-blue-400/80" />
                  <span className="truncate">{entry.name}</span>
                </button>
              ))}
              {listing && listing.entries.length === 0 && !listing.parent && (
                <p className="p-6 text-center text-xs text-muted-foreground/60">
                  No subfolders here.
                </p>
              )}
            </>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mx-5 mt-2 flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/[0.06] px-3 py-2 text-xs text-red-300">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{error}</span>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 px-5 py-4">
          <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-muted-foreground/60">
            {listing?.path ?? ""}
          </span>
          <Button
            onClick={() => void selectFolder()}
            disabled={!listing || submitting}
            size="sm"
            className="shrink-0 rounded-lg bg-gradient-to-r from-blue-500 to-violet-500 hover:from-blue-600 hover:to-violet-600 shadow-lg shadow-blue-500/20 disabled:opacity-40 disabled:shadow-none transition-all"
          >
            {submitting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Check className="h-3.5 w-3.5" />
            )}
            Select this folder
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
}
