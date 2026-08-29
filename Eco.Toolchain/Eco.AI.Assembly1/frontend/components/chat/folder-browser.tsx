"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Check,
  ChevronRight,
  CornerDownLeft,
  FolderClosed,
  FolderOpen,
  File as FileIcon,
  Home,
  Loader2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { FsListing, FsEntry, FsRoots } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";

interface FolderBrowserProps {
  onClose: () => void;
  // POST /api/projects returns the bare registry entry (no sessions yet).
  onAdded?: (project: { path: string; name: string; id: string }) => void;
  // When "file", the modal lists files alongside dirs and lets the user pick
  // one or many; onFilesSelected fires with the chosen file paths.
  mode?: "dir" | "file";
  allowMultiple?: boolean;
  onFilesSelected?: (files: { path: string; name: string; size: number }[]) => void;
  // D2: open at this path instead of home (used to root the attachment picker
  // at the active project directory).
  initialPath?: string;
  // Optional extra quick-link shown as a chip (e.g. the active project's
  // directory when adding a new project).
  anchorPath?: string;
}

// Modal folder picker backed by GET /api/fs/browse (directories only) and
// POST /api/projects to register the chosen folder. In file mode it also lists
// files and emits onFilesSelected instead of registering a project. Starts in
// the server's home directory (or initialPath); Explorer-style Back / Forward /
// Up buttons and a combined breadcrumb + editable address bar navigate the
// tree; GET /api/fs/roots feeds the quick-jump chips so it is obvious which
// locations the server (api container) is allowed to browse.
export function FolderBrowser({
  onClose,
  onAdded,
  mode = "dir",
  allowMultiple = false,
  onFilesSelected,
  initialPath,
  anchorPath,
}: FolderBrowserProps) {
  const [listing, setListing] = useState<FsListing | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pathDraft, setPathDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [rootsInfo, setRootsInfo] = useState<FsRoots | null>(null);
  // B2: accumulate selections across folder navigation in a Map<path, entry>
  // (not just the current directory) so multi-folder picks aren't lost.
  const [selected, setSelected] = useState<Map<string, FsEntry>>(new Map());
  // Explorer-style navigation history. Kept in refs (updated inside async
  // fetchListing without stale closures); navState just mirrors the
  // canBack/canForward flags for rendering.
  const historyRef = useRef<string[]>([]);
  const indexRef = useRef(-1);
  const [navState, setNavState] = useState({ canBack: false, canForward: false });
  const isFileMode = mode === "file";

  const syncNav = () =>
    setNavState({
      canBack: indexRef.current > 0,
      canForward: indexRef.current < historyRef.current.length - 1,
    });

  const fetchListing = useCallback(async (path?: string, options?: { push?: boolean }) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (path) params.set("path", path);
      if (isFileMode) params.set("files", "1");
      const qs = params.toString();
      const res = await fetch(`${API_URL}/api/fs/browse${qs ? `?${qs}` : ""}`);
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Request failed (${res.status})`);
      }
      const data = await res.json() as FsListing;
      setListing(data);
      // Record the resolved path (server may normalize it) in the history
      // stack unless we're re-visiting via back/forward.
      if (options?.push !== false && historyRef.current[indexRef.current] !== data.path) {
        historyRef.current = [...historyRef.current.slice(0, indexRef.current + 1), data.path];
        indexRef.current = historyRef.current.length - 1;
        syncNav();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to browse folders");
    } finally {
      setLoading(false);
    }
  }, [isFileMode]);

  const goBack = () => {
    if (indexRef.current <= 0) return;
    indexRef.current -= 1;
    syncNav();
    void fetchListing(historyRef.current[indexRef.current], { push: false });
  };

  const goForward = () => {
    if (indexRef.current >= historyRef.current.length - 1) return;
    indexRef.current += 1;
    syncNav();
    void fetchListing(historyRef.current[indexRef.current], { push: false });
  };

  const goUp = () => {
    if (listing?.parent) void fetchListing(listing.parent);
  };

  useEffect(() => {
    // D2: when an initialPath is supplied (e.g. the active project root for
    // the attachment picker) open there; otherwise fall back to home.
    if (!listing && loading) void fetchListing(initialPath);
    // Quick-jump chips: show the server's browsable roots so the picker makes
    // it obvious which filesystem (the api container's) is being listed.
    fetch(`${API_URL}/api/fs/roots`)
      .then((res) => (res.ok ? res.json() : null))
      .then((body: FsRoots | null) => body && setRootsInfo(body))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep the editable path field in sync with wherever the user navigates.
  useEffect(() => {
    if (listing) setPathDraft(listing.path);
  }, [listing]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (editing) { setEditing(false); if (listing) setPathDraft(listing.path); }
        else onClose();
        return;
      }
      // Don't hijack keys while the address bar has focus.
      if (event.target instanceof HTMLInputElement) return;
      if (event.altKey && event.key === "ArrowLeft") goBack();
      else if (event.altKey && event.key === "ArrowRight") goForward();
      else if (event.key === "Backspace") goUp();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editing, listing, onClose]);

  const submitPath = () => {
    const next = pathDraft.trim();
    if (next) void fetchListing(next);
    setEditing(false);
  };

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
      onAdded?.((await res.json()) as { path: string; name: string; id: string });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add project");
      setSubmitting(false);
    }
  };

  const toggleFile = (entry: FsEntry) => {
    setSelected((prev) => {
      const next = new Map(prev);
      if (next.has(entry.path)) {
        next.delete(entry.path);
      } else {
        if (!allowMultiple) next.clear();
        next.set(entry.path, entry);
      }
      return next;
    });
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
        className="w-full max-w-[min(56rem,92vw)] rounded-2xl border border-white/[0.08] glass-strong shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        {/* Title bar */}
        <div className="flex items-center justify-between px-5 pt-4 pb-3">
          <h2 className="text-sm font-semibold">
            {isFileMode ? "Choose files to attach" : "Choose project folder"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-foreground"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Explorer-style toolbar: Back / Forward / Up + breadcrumb address
            bar. The bar shows clickable breadcrumbs; clicking it switches to
            an editable absolute path (Enter opens, Escape cancels). */}
        <div className="mx-5 mb-2 space-y-1.5 select-none">
          <div className="flex items-stretch gap-1.5">
            <button
              type="button"
              onClick={goBack}
              disabled={!navState.canBack}
              title="Back (Alt+←)"
              aria-label="Back"
              className="shrink-0 rounded-lg border border-white/[0.06] bg-black/30 px-2 text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={goForward}
              disabled={!navState.canForward}
              title="Forward (Alt+→)"
              aria-label="Forward"
              className="shrink-0 rounded-lg border border-white/[0.06] bg-black/30 px-2 text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30"
            >
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={goUp}
              disabled={!listing?.parent}
              title="Up one level (Backspace)"
              aria-label="Up one level"
              className="shrink-0 rounded-lg border border-white/[0.06] bg-black/30 px-2 text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30"
            >
              <ArrowUp className="h-3.5 w-3.5" />
            </button>

            {editing ? (
              <form
                className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-blue-500/30 bg-black/40 px-3 py-1.5"
                onSubmit={(event) => { event.preventDefault(); submitPath(); }}
              >
                <input
                  autoFocus
                  value={pathDraft}
                  onChange={(event) => setPathDraft(event.target.value)}
                  onBlur={() => { setEditing(false); if (listing) setPathDraft(listing.path); }}
                  placeholder="Absolute path, e.g. /app/output"
                  spellCheck={false}
                  className="min-w-0 flex-1 bg-transparent font-mono text-[11px] text-foreground outline-none placeholder:text-muted-foreground/40"
                />
                <button
                  type="submit"
                  title="Open path"
                  className="shrink-0 rounded p-1 text-muted-foreground transition-colors hover:bg-white/[0.08] hover:text-foreground"
                >
                  <CornerDownLeft className="h-3 w-3" />
                </button>
              </form>
            ) : (
              <button
                type="button"
                onClick={() => setEditing(true)}
                title="Edit path"
                className="flex min-w-0 flex-1 items-center overflow-x-auto whitespace-nowrap rounded-lg border border-white/[0.06] bg-black/30 px-3 py-1.5 text-xs thin-scroll transition-colors hover:border-white/[0.12]"
              >
                {crumbs.map((crumb, index) => (
                  <span
                    key={crumb.path}
                    role="button"
                    tabIndex={-1}
                    onClick={(event) => {
                      // Clicking a crumb navigates directly instead of just
                      // entering edit mode.
                      event.stopPropagation();
                      void fetchListing(crumb.path);
                    }}
                    className="flex items-center shrink-0"
                  >
                    {index > 0 && <ChevronRight className="h-3 w-3 mx-0.5 text-muted-foreground/40" />}
                    <span
                      className={cn(
                        "rounded px-1 py-0.5 font-mono",
                        index === crumbs.length - 1
                          ? "text-blue-300"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {crumb.label}
                    </span>
                  </span>
                ))}
              </button>
            )}
          </div>

          {/* Quick jumps: locations this server is allowed to browse. In the
              dev stack these live inside the api container, not on the browser
              host — the chips make that filesystem concrete. Each chip is
              labeled with its role so the raw paths read meaningfully. */}
          {rootsInfo && rootsInfo.roots.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 px-0.5">
              <span className="shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground/50">
                Go to
              </span>
              {anchorPath && (
                <button
                  type="button"
                  onClick={() => void fetchListing(anchorPath)}
                  title={`Active project: ${anchorPath}`}
                  className={cn(
                    "flex max-w-full items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] transition-colors",
                    anchorPath === listing?.path
                      ? "border-violet-500/50 bg-violet-500/[0.16] text-violet-100"
                      : "border-violet-500/25 bg-violet-500/[0.08] text-violet-200 hover:bg-violet-500/[0.16]",
                  )}
                >
                  <FolderOpen className="h-3 w-3 shrink-0" />
                  <span className="shrink-0 font-medium">Active project</span>
                  <span className="truncate font-mono opacity-80">· {anchorPath}</span>
                </button>
              )}
              {rootsInfo.roots.map((root) => {
                const isHome = root === rootsInfo.home;
                const isOutput = root === rootsInfo.output_root;
                const role = isHome ? "Home" : isOutput ? "Output root" : root.split("/").filter(Boolean).pop() || root;
                return (
                  <button
                    key={root}
                    type="button"
                    onClick={() => void fetchListing(root)}
                    title={`${isHome ? "Home directory" : isOutput ? "Harness output root" : "Allowed root"}: ${root}`}
                    className={cn(
                      "flex max-w-full items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] transition-colors",
                      root === listing?.path
                        ? "border-blue-500/50 bg-blue-500/[0.14] text-blue-100"
                        : "border-white/[0.08] bg-white/[0.03] text-muted-foreground hover:bg-white/[0.07] hover:text-foreground",
                    )}
                  >
                    {isHome && <Home className="h-3 w-3 shrink-0" />}
                    <span className="shrink-0 font-medium">{role}</span>
                    <span className="truncate font-mono opacity-70">· {root}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Directory / file list. select-none: rapid Back/Up clicking must
            not sweep-select the row labels (browser text selection). */}
        <div className="mx-5 h-64 select-none overflow-y-auto rounded-xl border border-white/[0.06] bg-white/[0.02] thin-scroll">
          {loading ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : (
            <>
              {listing?.entries.map((entry) => {
                const isFile = entry.type === "file";
                const isChecked = isFile && selected.has(entry.path);
                return (
                  <button
                    key={entry.path}
                    type="button"
                    onClick={() => {
                      if (isFile) toggleFile(entry);
                      else void fetchListing(entry.path);
                    }}
                    className={cn(
                      "flex w-full items-center gap-2.5 px-4 py-2 text-left text-xs transition-colors hover:bg-white/[0.05]",
                      isChecked && "bg-blue-500/10",
                    )}
                  >
                    {isFile ? (
                      <FileIcon className="h-3.5 w-3.5 shrink-0 text-amber-300/80" />
                    ) : (
                      <FolderClosed className="h-3.5 w-3.5 shrink-0 text-blue-400/80" />
                    )}
                    <span className="min-w-0 flex-1 truncate">{entry.name}</span>
                    {isFile && entry.size != null && (
                      <span className="shrink-0 font-mono text-[10px] text-muted-foreground/50">
                        {(entry.size / 1024).toFixed(entry.size < 1024 ? 0 : 1)} KB
                      </span>
                    )}
                    {isChecked && <Check className="h-3.5 w-3.5 shrink-0 text-blue-300" />}
                  </button>
                );
              })}
              {listing && listing.entries.length === 0 && !listing.parent && (
                <p className="p-6 text-center text-xs text-muted-foreground/60">
                  {isFileMode ? "No files or subfolders here." : "No subfolders here."}
                </p>
              )}
            </>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mx-5 mt-2 space-y-1 rounded-lg border border-red-500/20 bg-red-500/[0.06] px-3 py-2 text-xs text-red-300">
            <div className="flex items-start gap-2">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {/* break-words, not truncate: the "outside the allowed roots"
                  detail names the offending path and must stay readable. */}
              <span className="break-words">{error}</span>
            </div>
            {/allowed roots/i.test(error) && rootsInfo && (
              <p className="break-words pl-6 text-[10px] leading-relaxed text-red-300/70">
                The picker browses the server&apos;s filesystem (inside the api
                container), not this browser machine&apos;s disks. Allowed roots:{" "}
                {rootsInfo.roots.join(", ")}
              </p>
            )}
          </div>
        )}

        {/* Footer: the folder that "Select" will register, emphasized and
            wrapped so long paths are fully readable. */}
        <div className="flex items-center justify-between gap-3 px-5 py-4">
          <div className="flex min-w-0 flex-1 items-start gap-1.5">
            <FolderClosed className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-400/80" />
            <div className="min-w-0">
              <div className="text-[9px] uppercase tracking-wider text-muted-foreground/50">
                {isFileMode ? "Browsing in" : "Selected folder"}
              </div>
              <div className="break-all font-mono text-[11px] leading-snug text-foreground/80">
                {listing?.path ?? "—"}
              </div>
            </div>
          </div>
          {isFileMode ? (
            <Button
              onClick={() => {
                // B2: build the payload from the accumulated selection map,
                // not just the current directory's entries.
                const files = Array.from(selected.values()).map((e) => ({
                  path: e.path,
                  name: e.name,
                  size: e.size ?? 0,
                }));
                onFilesSelected?.(files);
              }}
              disabled={selected.size === 0}
              size="sm"
              className="shrink-0 rounded-lg bg-gradient-to-r from-blue-500 to-violet-500 hover:from-blue-600 hover:to-violet-600 shadow-lg shadow-blue-500/20 disabled:opacity-40 disabled:shadow-none transition-all"
            >
              {submitting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Check className="h-3.5 w-3.5" />
              )}
              Add {selected.size > 0 ? selected.size : ""} file{selected.size === 1 ? "" : "s"}
            </Button>
          ) : (
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
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
