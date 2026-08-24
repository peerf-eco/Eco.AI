"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send, Bot, User, Settings, X, Sparkles, StopCircle,
  GitBranch, Workflow, Plus, File as FileIcon, Image as ImageIcon,
  FolderClosed as FolderClosedIcon, AlertCircle as AlertCircleIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { PhaseStepper } from "./phase-stepper";
import { StreamMessage } from "./stream-message";
import { useHarnessSocket } from "./use-socket";
import { Dropdown, type DropdownOption } from "./dropdown";
import { PlatformSelector, PLATFORM_OPTIONS, DEFAULT_PLATFORM, type PlatformOption } from "./platform-selector";
import { LanguageSelector, LANGUAGE_OPTIONS, type ProgrammingLanguage } from "./language-selector";
import { ProjectsPanel, type ExportFormat } from "./project-panel";
import { FolderBrowser } from "./folder-browser";
import { EcoosLogo } from "./ecoos-logo";
import { AgentSettings } from "./agent-settings";
import type {
  Attachment, AttachmentKind, ChatMessage, FsEntry, ProjectInfo, WorkingMode,
} from "./types";

const MAX_PASTE_BYTES = 5 * 1024 * 1024; // 5 MB cap on pasted/base64 content

function guessKind(name: string): AttachmentKind {
  return /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(name) ? "image" : "text";
}

// Relative path of `absPath` against the active project root for the @-mention
// token. Files inside the root become relative; everything else stays absolute.
function relativePath(absPath: string, root?: string | null): string {
  if (!root) return absPath;
  const base = root.endsWith("/") ? root : `${root}/`;
  if (absPath === root) {
    return absPath.split("/").filter(Boolean).pop() ?? absPath;
  }
  if (absPath.startsWith(base)) return absPath.slice(base.length);
  return absPath;
}

const PLATFORM_STORAGE_KEY = "eco_harness.target_platform";
const LANGUAGE_STORAGE_KEY = "eco_harness.language";
const PANEL_OPEN_STORAGE_KEY = "eco_harness.panel_open";
const ACTIVE_PROJECT_STORAGE_KEY = "eco_harness.active_project";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";
const WS_BASE = API_URL.replace(/^http/, "ws");
// Optimization 3: cap total per-message attachment bytes. Pasted images are
// base64 in the JSON WS frame; a few large ones can blow past uvicorn's 16 MB
// default and silently drop the connection. Keep a safe headroom under that.
const MAX_TOTAL_ATTACH_BYTES = 12 * 1024 * 1024;

const MODE_OPTIONS: DropdownOption<WorkingMode>[] = [
  { value: "auto", label: "Auto · loop" },
  { value: "plan", label: "Plan" },
  { value: "code", label: "Code" },
  { value: "migrate", label: "Migrate" },
  { value: "test", label: "Test" },
  { value: "review", label: "Review" },
];

const EXAMPLES = [
  "Собери калькулятор с pow и sqrt",
  "Создай приложение, выводящее sin/cos для углов от 0 до 90",
  "Сделай конвертер температур из Цельсия в Фаренгейт",
];

export function ChatInterface() {
  const [input, setInput] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  // Persist target selection after mount to avoid SSR mismatch.
  const [platform, setPlatform] = useState<PlatformOption>(DEFAULT_PLATFORM);
  const [language, setLanguage] = useState<ProgrammingLanguage>("C");
  const [mode, setMode] = useState<WorkingMode>("auto");
  const [useWorktree, setUseWorktree] = useState(false);
  const scrollAnchorRef = useRef<HTMLTextAreaElement>(null);

  // Left projects panel state.
  const [panelOpen, setPanelOpen] = useState(true);
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [browserOpen, setBrowserOpen] = useState(false);
  const [fileBrowserOpen, setFileBrowserOpen] = useState(false);
  // Panel feedback (removal blocked, export errors) + in-flight export marker.
  const [panelNotice, setPanelNotice] = useState<string | null>(null);
  const [exportBusy, setExportBusy] = useState(false);

  // Session-scoped attachments (decision #1): available to every message in the
  // current session, cleared on New Session. Kept in component state so the
  // in-flight run and the next message both carry them.
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [pasteError, setPasteError] = useState<string | null>(null);

  // @-mention autocomplete state machine.
  const [mention, setMention] = useState<{
    active: boolean; query: string; start: number; index: number;
  } | null>(null);
  const [mentionHits, setMentionHits] = useState<FsEntry[]>([]);
  const [mentionLoading, setMentionLoading] = useState(false);
  const mentionPopoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(PLATFORM_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        const match = PLATFORM_OPTIONS.find(
          (p) => p.os === parsed.os && p.arch === parsed.arch,
        );
        if (match) setPlatform(match);
      }
    } catch {
      // ignore — corrupt storage just falls back to default
    }
    const storedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (storedLanguage && LANGUAGE_OPTIONS.includes(storedLanguage as ProgrammingLanguage)) {
      setLanguage(storedLanguage as ProgrammingLanguage);
    }
    setPanelOpen(window.localStorage.getItem(PANEL_OPEN_STORAGE_KEY) !== "0");
    setActiveProjectId(window.localStorage.getItem(ACTIVE_PROJECT_STORAGE_KEY));
  }, []);

  const refreshProjects = useCallback(async (): Promise<ProjectInfo[]> => {
    try {
      const res = await fetch(`${API_URL}/api/projects`);
      if (!res.ok) return [];
      const data = await res.json();
      const list: ProjectInfo[] = data.projects ?? [];
      setProjects(list);
      return list;
    } catch {
      return [];
    }
  }, []);

  useEffect(() => {
    void refreshProjects();
  }, [refreshProjects]);

  const handleSelectProject = useCallback((project: ProjectInfo) => {
    setActiveProjectId(project.id);
    try {
      window.localStorage.setItem(ACTIVE_PROJECT_STORAGE_KEY, project.id);
    } catch {
      // ignore
    }
  }, []);

  const handleTogglePanel = useCallback(() => {
    setPanelOpen((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(PANEL_OPEN_STORAGE_KEY, next ? "1" : "0");
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  const handleProjectAdded = useCallback(async (entry: { path: string }) => {
    setBrowserOpen(false);
    const list = await refreshProjects();
    const match = list.find((p) => p.path === entry.path);
    if (match) handleSelectProject(match);
  }, [refreshProjects, handleSelectProject]);

  // ── Panel actions: whitelist removal + session export downloads ───────────
  // Removal is visual only server-side; on failure (409 running session etc.)
  // surface the reason as a dismissible panel notice. The panel list is
  // refreshed either way and the auto-reselect effect covers the removed
  // active project.
  const handleRemoveProject = useCallback(async (project: ProjectInfo) => {
    setPanelNotice(null);
    try {
      const res = await fetch(`${API_URL}/api/projects/${project.id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setPanelNotice(
          body?.detail
            ? `Cannot remove "${project.name}": ${body.detail}`
            : `Cannot remove "${project.name}" (HTTP ${res.status})`,
        );
      }
    } catch {
      setPanelNotice(`Cannot remove "${project.name}": backend unreachable`);
    }
    await refreshProjects();
  }, [refreshProjects]);

  const downloadExport = useCallback(async (url: string, fallbackName: string) => {
    setExportBusy(true);
    setPanelNotice(null);
    try {
      const res = await fetch(url);
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setPanelNotice(body?.detail ?? `Export failed (HTTP ${res.status})`);
        return;
      }
      const blob = await res.blob();
      const match = (res.headers.get("Content-Disposition") ?? "")
        .match(/filename="?([^";]+)"?/i);
      const href = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download = match?.[1] || fallbackName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(href);
    } catch {
      setPanelNotice("Export failed: backend unreachable");
    } finally {
      setExportBusy(false);
    }
  }, []);

  const handleExportProject = useCallback(
    (project: ProjectInfo, format: ExportFormat) => {
      void downloadExport(
        `${API_URL}/api/projects/${project.id}/export?format=${format}`,
        `${project.name}-sessions.${format}`,
      );
    },
    [downloadExport],
  );

  const handleExportAll = useCallback(
    (format: ExportFormat) => {
      void downloadExport(
        `${API_URL}/api/export/all?format=${format}`,
        `harness-sessions-all.${format}`,
      );
    },
    [downloadExport],
  );

  const activeProject = projects.find((p) => p.id === activeProjectId) ?? null;

  // Until the user explicitly picks a project, keep the most recently active
  // one highlighted so the panel and header always reflect a current project.
  useEffect(() => {
    if (projects.length === 0) return;
    if (activeProjectId && projects.some((p) => p.id === activeProjectId)) return;
    const lastActivity = (project: ProjectInfo) =>
      Date.parse(project.sessions[0]?.updated_at ?? project.added_at) || 0;
    const mostRecent = [...projects].sort(
      (a, b) => lastActivity(b) - lastActivity(a),
    )[0];
    handleSelectProject(mostRecent);
  }, [projects, activeProjectId, handleSelectProject]);

  // ── Attachments ────────────────────────────────────────────────────────────
  // Revoke a blob: URL so pasted-image previews don't leak (optimization 4).
  const revokeAttachment = useCallback((a: Attachment) => {
    if (a.previewUrl && a.previewUrl.startsWith("blob:")) {
      URL.revokeObjectURL(a.previewUrl);
    }
  }, []);

  const addAttachment = useCallback((a: Attachment) => {
    setAttachments((prev) => {
      const key = a.path ?? `${a.name}:${a.size ?? 0}`;
      if (prev.some((p) => (p.path ?? `${p.name}:${p.size ?? 0}`) === key)) return prev;
      return [...prev, a];
    });
  }, []);

  // Removing a chip does NOT revoke its previewUrl: sent message bubbles share
  // the same Attachment object, so an early revoke would break their
  // thumbnails. Blob URLs are reclaimed on New Session (chat cleared) and on
  // unmount — bounded and leak-free.
  const removeAttachment = useCallback((id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const attachmentBytes = attachments.reduce((sum, a) => sum + (a.size ?? 0), 0);

  // Unmount cleanup for any blob: previews still alive (New Session already
  // revokes; this covers navigation away mid-session).
  const attachmentsRef = useRef(attachments);
  attachmentsRef.current = attachments;
  useEffect(() => {
    return () => {
      attachmentsRef.current.forEach(revokeAttachment);
    };
  }, [revokeAttachment]);

  // ── @-mention autocomplete ──────────────────────────────────────────────────
  const detectMention = useCallback((value: string, caret: number) => {
    let i = caret - 1;
    while (i >= 0 && !/\s/.test(value[i])) i--;
    const atPos = i + 1;
    if (atPos < caret && value[atPos] === "@") {
      setMention({ active: true, query: value.slice(atPos + 1, caret), start: atPos, index: 0 });
    } else {
      setMention(null);
    }
  }, []);

  const selectMention = useCallback((hit: FsEntry) => {
    if (!mention) return;
    const before = input.slice(0, mention.start);
    const after = input.slice(mention.start + 1 + mention.query.length);
    const rel = relativePath(hit.path, activeProject?.path);
    const token = `@${rel} `;
    const newInput = before + token + after;
    setInput(newInput);
    const caretPos = (before + token).length;
    requestAnimationFrame(() => {
      const el = scrollAnchorRef.current;
      if (el) {
        el.focus();
        el.setSelectionRange(caretPos, caretPos);
      }
    });
    addAttachment({
      id: crypto.randomUUID(),
      name: hit.name,
      path: hit.path,
      kind: guessKind(hit.name),
      size: hit.size,
      source: "mention",
    });
    setMention(null);
  }, [mention, input, activeProject?.path, addAttachment]);

  // Debounced fetch of mention hits from /api/fs/search.
  useEffect(() => {
    if (!mention?.active || mention.query.length < 1) {
      setMentionHits([]);
      return;
    }
    const q = mention.query;
    const root = activeProject?.path ?? "";
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      setMentionLoading(true);
      try {
        const params = new URLSearchParams({ q, limit: "50", depth: "8", backend: "os_walk" });
        if (root) params.set("root", root);
        const res = await fetch(`${API_URL}/api/fs/search?${params.toString()}`, {
          signal: ctrl.signal,
        });
        if (!res.ok) return;
        const data = await res.json();
        // Search returns files only; tag each as "file" to satisfy FsEntry.
        setMentionHits(
          (data.results ?? []).map((r: { name: string; path: string; size?: number }) => ({
            ...r,
            type: "file" as const,
          })),
        );
      } catch {
        // aborted or network error — keep prior hits
      } finally {
        setMentionLoading(false);
      }
    }, 150);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [mention?.active, mention?.query, activeProject?.path]);

  // B5: close the @-mention popover on any outside mousedown (Escape and typing
  // already close it). Clicking inside the textarea or the popover keeps it.
  useEffect(() => {
    if (!mention?.active) return;
    const onDocMouseDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (
        scrollAnchorRef.current?.contains(t) ||
        mentionPopoverRef.current?.contains(t)
      ) {
        return;
      }
      setMention(null);
    };
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [mention?.active]);

  // ── Paste & drop ───────────────────────────────────────────────────────────
  const addPastedFile = useCallback((file: File, kind: AttachmentKind) => {
    if (file.size > MAX_PASTE_BYTES) {
      setPasteError(
        `"${file.name || "file"}" is larger than 5 MB — add it with the + picker instead.`,
      );
      return;
    }
    const id = crypto.randomUUID();
    const name = file.name ||
      (kind === "image" ? `pasted-${Date.now()}.png` : `pasted-${Date.now()}.txt`);
    const reader = new FileReader();
    reader.onload = () => {
      if (kind === "image") {
        const dataUrl = reader.result as string;
        addAttachment({
          id, name, kind, mime: file.type, size: file.size,
          content: dataUrl, previewUrl: URL.createObjectURL(file), source: "paste",
        });
      } else {
        addAttachment({
          id, name, kind, mime: file.type, size: file.size,
          content: reader.result as string, source: "paste",
        });
      }
    };
    reader.onerror = () => {
      setPasteError(`Failed to read "${name}" — try the + picker instead.`);
    };
    if (kind === "image") reader.readAsDataURL(file);
    else reader.readAsText(file);
  }, [addAttachment]);

  const onPaste = useCallback((e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = Array.from(e.clipboardData.items);
    let handled = false;
    for (const it of items) {
      if (it.kind === "file" && it.type.startsWith("image/")) {
        const file = it.getAsFile();
        if (file) { addPastedFile(file, "image"); handled = true; }
      } else if (it.kind === "file" && it.type.startsWith("text/")) {
        const file = it.getAsFile();
        if (file) { addPastedFile(file, "text"); handled = true; }
      }
    }
    // Plain text paste: let default insertion happen (do not preventDefault).
    if (handled) e.preventDefault();
  }, [addPastedFile]);

  const onDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    const files = Array.from(e.dataTransfer?.files ?? []);
    if (files.length === 0) return;
    e.preventDefault();
    for (const file of files) addPastedFile(file, guessKind(file.name));
  }, [addPastedFile]);

  const onDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    if (e.dataTransfer?.files?.length) e.preventDefault();
  }, []);

  const {
    messages,
    isConnected,
    isProcessing,
    currentPhase,
    completedPhases,
    threadId,
    worktree,
    sendUserRequest,
    sendPlanDecision,
    sendEscalationDecision,
    sendAbort,
    clearMessages,
  } = useHarnessSocket(WS_BASE);

  // New Session: clear messages (rolls a fresh thread) and drop attachments.
  // Settings (platform/language/mode/useWorktree/project) intentionally persist.
  const handleNewSession = useCallback(() => {
    if (isProcessing) return;
    attachments.forEach(revokeAttachment);
    setAttachments([]);
    setMention(null);
    setPasteError(null);
    clearMessages();
  }, [isProcessing, clearMessages, attachments, revokeAttachment]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-grow textarea: tracks content height, capped so huge prompts stay
  // scrollable instead of swallowing the chat area.
  useEffect(() => {
    const el = scrollAnchorRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  // When a run settles, refresh the panel so the finished session shows up
  // under its project without a manual page reload.
  const wasProcessing = useRef(false);
  useEffect(() => {
    if (wasProcessing.current && !isProcessing) void refreshProjects();
    wasProcessing.current = isProcessing;
  }, [isProcessing, refreshProjects]);

  const onSend = () => {
    if (!input.trim() || !isConnected || isProcessing) return;
    // Optimization 3: refuse oversized attachment payloads before they can
    // silently drop the WS connection.
    if (attachmentBytes > MAX_TOTAL_ATTACH_BYTES) {
      setPasteError(
        "Attachments are too large for a single message (max ~12 MB). " +
        "Remove some or add them via the + picker instead.",
      );
      return;
    }
    sendUserRequest(input, {
      targetOs: platform.os,
      targetArch: platform.arch,
      language,
      mode,
      useWorktree,
      projectDir: activeProject?.path,
      attachedFiles: attachments,
    });
    setInput("");
    // B1: close any open @-mention popover so it can't inject a stale hit into
    // the next message.
    setMention(null);
  };

  const handleLanguageChange = (next: ProgrammingLanguage) => {
    setLanguage(next);
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, next);
  };

  const handlePlatformChange = (p: PlatformOption) => {
    setPlatform(p);
    try {
      window.localStorage.setItem(PLATFORM_STORAGE_KEY, JSON.stringify({ os: p.os, arch: p.arch }));
    } catch {
      // localStorage full / blocked — silently ignore, state still updates
    }
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Ambient glow */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/[0.03] rounded-full blur-[128px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-violet-500/[0.03] rounded-full blur-[128px]" />
      </div>

      {/* Left projects panel */}
      <ProjectsPanel
        open={panelOpen}
        onToggle={handleTogglePanel}
        projects={projects}
        activeProjectId={activeProjectId}
        onSelect={handleSelectProject}
        onNewProject={() => setBrowserOpen(true)}
        onRemoveProject={handleRemoveProject}
        onExportProject={handleExportProject}
        onExportAll={handleExportAll}
        exportBusy={exportBusy}
        notice={panelNotice}
        onDismissNotice={() => setPanelNotice(null)}
      />

      {/* Settings sidebar */}
      <AnimatePresence>
        {showSettings && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
              onClick={() => setShowSettings(false)}
            />
            <motion.div
              initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="fixed inset-y-0 right-0 z-50 flex w-[26rem] flex-col glass-strong shadow-2xl"
            >
              <div className="flex items-center justify-between px-5 pb-4 pt-5">
                <h2 className="text-lg font-semibold text-gradient">Settings</h2>
                <Button variant="ghost" size="icon" onClick={() => setShowSettings(false)} className="hover:bg-white/10">
                  <X className="h-4 w-4" />
                </Button>
              </div>
              {threadId && (
                <div className="mx-5 mb-4 flex items-center gap-2 rounded-lg border border-white/[0.06] bg-black/20 px-3 py-2">
                  <div className="min-w-0 flex-1">
                    <div className="text-[9px] uppercase tracking-wider text-muted-foreground/60">Thread</div>
                    <div className="truncate font-mono text-[11px] text-foreground/70">{threadId}</div>
                  </div>
                </div>
              )}
              <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-2 thin-scroll">
                <AgentSettings />
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Folder browser (project picker) */}
      <AnimatePresence>
        {browserOpen && (
          <FolderBrowser onClose={() => setBrowserOpen(false)} onAdded={handleProjectAdded} />
        )}
      </AnimatePresence>

      {/* File browser (attachment picker) */}
      <AnimatePresence>
        {fileBrowserOpen && (
          <FolderBrowser
            mode="file"
            allowMultiple
            initialPath={activeProject?.path}
            onClose={() => setFileBrowserOpen(false)}
            onFilesSelected={(files) => {
              files.forEach((f) => addAttachment({
                id: crypto.randomUUID(),
                name: f.name,
                path: f.path,
                kind: guessKind(f.name),
                size: f.size,
                source: "picker",
              }));
              setFileBrowserOpen(false);
            }}
          />
        )}
      </AnimatePresence>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col relative z-10">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-3.5 glass border-b border-white/[0.06]">
          <div className="flex items-center gap-3 min-w-0">
            <EcoosLogo className="h-9 w-9 shrink-0" />
            <div className="min-w-0">
              <h1 className="truncate text-base font-semibold tracking-tight">
                EcoOS Component Agent
              </h1>
              {activeProject ? (
                <p
                  className="truncate text-xs text-muted-foreground"
                  title={`Project folder — the directory the agent reads and writes for every request in this session:\n${activeProject.path}`}
                >
                  Working in{" "}
                  <span className="font-mono text-blue-300/90" title={activeProject.name}>
                    {activeProject.name}
                  </span>
                  <span className="ml-1.5 font-mono text-muted-foreground/40" title={activeProject.path}>
                    {activeProject.path}
                  </span>
                </p>
              ) : (
                <p className="truncate text-xs text-muted-foreground">
                  ACOM Meta-Harness
                </p>
              )}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <div className="flex items-center gap-2 rounded-full glass px-3 py-1.5">
              <div className={cn(
                "h-2 w-2 rounded-full transition-colors",
                isConnected
                  ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]"
                  : "bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.5)]",
              )} />
              <span className="text-xs text-muted-foreground">
                {isConnected ? "Connected" : "Reconnecting…"}
              </span>
            </div>
            {messages.length > 0 && (
              <Button
                variant="ghost"
                onClick={handleNewSession}
                disabled={isProcessing}
                className="rounded-lg hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed"
                title="Start a fresh session (clears messages and attachments, keeps your settings)"
              >
                New Session
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowSettings(true)}
              className="hover:bg-white/10 rounded-lg"
            >
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </header>

        {/* Phase stepper */}
        <PhaseStepper currentPhase={currentPhase} completedPhases={completedPhases} />

        {/* Worktree reference strip — appears once the backend isolates this
            session into its own git worktree; stays visible after completion
            so the name/path can be looked up on disk or via `git worktree list`. */}
        {worktree && (
          <div className="flex items-center gap-2 px-6 py-1.5 border-b border-white/[0.06] bg-blue-500/[0.03] text-[11px]">
            <GitBranch className="h-3 w-3 shrink-0 text-blue-400" />
            <span
              className="shrink-0 font-mono text-blue-200/90"
              title={`Isolated git worktree (detached HEAD) created for this session.\nOn disk: ${worktree.path}\nFind it later: git worktree list`}
            >
              {worktree.name}
            </span>
            <span
              className="min-w-0 flex-1 truncate font-mono text-muted-foreground/50"
              title={worktree.path}
            >
              {worktree.path}
            </span>
          </div>
        )}

        {/* Chat area */}
        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-3xl px-4 py-6 space-y-5">
            {messages.length === 0 && !isProcessing && (
              <EmptyState onPick={setInput} />
            )}

            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                msg.role === "user"
                  ? <UserBubble key={msg.id} message={msg} />
                  : <StreamMessage
                      key={msg.id}
                      message={msg}
                      disabled={isProcessing}
                      onPlanDecision={sendPlanDecision}
                      onEscalationDecision={sendEscalationDecision}
                    />
              ))}
            </AnimatePresence>

            {isProcessing && <ProcessingPing />}

            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Input dock — message box on top, selector row inside the frame below */}
        <div className="px-4 pb-4 pt-2">
          <div className="mx-auto max-w-3xl">
            <div
              className="relative rounded-2xl glass-strong shadow-2xl transition-colors focus-within:border-blue-500/30 focus-within:glow-blue border border-transparent"
              onDrop={onDrop}
              onDragOver={onDragOver}
            >
              {/* Attachment chips + @-mention popover live inside the frame,
                  above the textarea. */}
              {attachments.length > 0 && (
                <div className="flex flex-wrap gap-1.5 px-3 pt-3">
                  {attachments.map((a) => (
                    <AttachmentChip
                      key={a.id}
                      attachment={a}
                      onRemove={() => removeAttachment(a.id)}
                    />
                  ))}
                </div>
              )}
              {attachmentBytes > 150 * 1024 && (
                <p className="px-3 pt-1 text-[10px] text-amber-300/80">
                  Large context — big files will be referenced, not inlined.
                </p>
              )}
              {pasteError && (
                <div className="flex items-center gap-2 px-3 pt-1 text-[10px] text-red-300/90">
                  <AlertCircleIcon className="h-3 w-3 shrink-0" />
                  <span>{pasteError}</span>
                  <button
                    type="button"
                    onClick={() => setPasteError(null)}
                    className="ml-auto rounded p-0.5 hover:bg-white/10"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              )}

              <textarea
                ref={scrollAnchorRef}
                rows={1}
                placeholder="Type a message…  Use @ to attach a file, drag & drop or paste images."
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  const caret = e.target.selectionStart ?? e.target.value.length;
                  detectMention(e.target.value, caret);
                }}
                onKeyDown={(e) => {
                  if (mention?.active && mentionHits.length > 0) {
                    if (e.key === "ArrowDown") {
                      e.preventDefault();
                      setMention((m) => m && { ...m, index: (m.index + 1) % mentionHits.length });
                      return;
                    }
                    if (e.key === "ArrowUp") {
                      e.preventDefault();
                      setMention((m) => m && {
                        ...m,
                        index: (m.index - 1 + mentionHits.length) % mentionHits.length,
                      });
                      return;
                    }
                    if (e.key === "Enter" || e.key === "Tab") {
                      e.preventDefault();
                      selectMention(mentionHits[mention.index] ?? mentionHits[0]);
                      return;
                    }
                    if (e.key === "Escape") {
                      e.preventDefault();
                      setMention(null);
                      return;
                    }
                  }
                  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault();
                    onSend();
                  }
                }}
                onPaste={onPaste}
                disabled={!isConnected || isProcessing}
                className="block w-full resize-none bg-transparent px-4 pb-1 pt-3.5 text-sm outline-none placeholder:text-muted-foreground/60 disabled:opacity-50"
              />

              {/* @-mention autocomplete popover — absolutely positioned above
                  the textarea. onMouseDown preventDefault keeps the textarea
                  focused so the click reaches selectMention. Only shown once a
                  query is typed so we don't flash "No matches" on a bare "@". */}
              {mention?.active && mention.query.length >= 1 && (
                <div
                  ref={mentionPopoverRef}
                  className="absolute bottom-full left-0 z-30 mb-2 w-80 max-w-[90%] max-h-64 overflow-y-auto rounded-xl border border-white/[0.08] glass-strong shadow-2xl thin-scroll"
                  onMouseDown={(e) => e.preventDefault()}
                >
                  {mentionLoading && mentionHits.length === 0 && (
                    <div className="px-3 py-2 text-xs text-muted-foreground">Searching…</div>
                  )}
                  {mentionHits.length === 0 && !mentionLoading && (
                    <div className="px-3 py-2 text-xs text-muted-foreground">No matches</div>
                  )}
                  {mentionHits.map((hit, i) => {
                    const rel = relativePath(hit.path, activeProject?.path);
                    return (
                      <button
                        key={hit.path}
                        type="button"
                        onMouseDown={(e) => {
                          e.preventDefault();
                          selectMention(hit);
                        }}
                        className={cn(
                          "flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors",
                          i === mention.index ? "bg-blue-500/15" : "hover:bg-white/[0.05]",
                        )}
                      >
                        {hit.type === "file" ? (
                          <FileIcon className="h-3.5 w-3.5 shrink-0 text-amber-300/80" />
                        ) : (
                          <FolderClosedIcon className="h-3.5 w-3.5 shrink-0 text-blue-400/80" />
                        )}
                        <span className="min-w-0 flex-1 truncate">{hit.name}</span>
                        <span className="shrink-0 font-mono text-[10px] text-muted-foreground/50">
                          {rel}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}

              <div className="flex items-center gap-1.5 px-2 pb-2 pt-1.5">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => setFileBrowserOpen(true)}
                  disabled={isProcessing}
                  className="shrink-0 rounded-lg hover:bg-white/10 disabled:opacity-40"
                  title="Attach files from the project"
                >
                  <Plus className="h-4 w-4" />
                </Button>
                <PlatformSelector
                  value={platform}
                  onChange={handlePlatformChange}
                  disabled={isProcessing}
                />
                <LanguageSelector
                  value={language}
                  onChange={handleLanguageChange}
                  disabled={isProcessing}
                />
                <Dropdown
                  value={mode}
                  options={MODE_OPTIONS}
                  onChange={(next) => setMode(next)}
                  icon={<Workflow className="h-3 w-3 shrink-0 text-emerald-400" />}
                  disabled={isProcessing}
                  title="How the harness handles this request"
                />
                <button
                  type="button"
                  onClick={() => setUseWorktree((v) => !v)}
                  disabled={isProcessing}
                  title="Run in an isolated git worktree"
                  className={cn(
                    "flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-xs transition-colors",
                    useWorktree
                      ? "border border-blue-500/40 bg-blue-500/15 text-blue-200"
                      : "border border-white/[0.08] bg-white/[0.05] text-foreground/90 hover:bg-white/[0.09]",
                    isProcessing && "cursor-not-allowed opacity-50",
                  )}
                >
                  <GitBranch className="h-3 w-3 shrink-0" />
                  Worktree
                </button>
                <div className="flex-1" />
                {isProcessing ? (
                  <Button
                    onClick={sendAbort}
                    size="icon"
                    variant="ghost"
                    className="shrink-0 rounded-full hover:bg-red-500/10 hover:text-red-400"
                    title="Stop"
                  >
                    <StopCircle size={18} />
                  </Button>
                ) : (
                  <Button
                    onClick={onSend}
                    disabled={!isConnected || !input.trim()}
                    size="icon"
                    className="shrink-0 rounded-full bg-gradient-to-r from-blue-500 to-violet-500 hover:from-blue-600 hover:to-violet-600 shadow-lg shadow-blue-500/20 disabled:opacity-30 disabled:shadow-none transition-all"
                    title="Send"
                  >
                    <Send size={16} />
                  </Button>
                )}
              </div>
            </div>
            <p className="mt-1.5 text-center text-[10px] text-muted-foreground/50">
              Enter to send · Shift+Enter for a new line
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Sub-components
// ────────────────────────────────────────────────────────────────────────────

function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="flex flex-col items-center justify-center pt-24 text-center"
    >
      <div className="relative mb-6">
        <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-violet-500/20 border border-white/10">
          <Sparkles className="h-10 w-10 text-blue-400 animate-float" />
        </div>
        <div className="absolute -inset-4 bg-blue-500/10 rounded-3xl blur-2xl -z-10" />
      </div>
      <h2 className="text-xl font-semibold mb-2">EcoOS Component Agent</h2>
      <p className="text-sm text-muted-foreground max-w-md leading-relaxed">
        Опишите приложение — агент составит план, скачает SDK, напишет код,
        соберёт и протестирует.
      </p>
      <div className="flex flex-wrap gap-2 mt-6 justify-center">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => onPick(ex)}
            className="rounded-lg glass px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-white/[0.06] transition-colors"
          >
            {ex}
          </button>
        ))}
      </div>
    </motion.div>
  );
}

function UserBubble({ message }: { message: ChatMessage }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1, transition: { duration: 0.15 } }}
      className="flex gap-3 flex-row-reverse"
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-violet-500 text-white shadow-lg shadow-blue-500/20">
        <User size={14} />
      </div>
      <div className="flex max-w-[80%] flex-col gap-2">
        <div className="rounded-xl px-4 py-3 bg-gradient-to-r from-blue-600/80 to-violet-600/80 text-white shadow-lg shadow-blue-500/10">
          <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.text}</div>
          {message.attachments && message.attachments.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {message.attachments.map((a) => (
                <AttachmentChip key={a.id} attachment={a} />
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function AttachmentChip({
  attachment,
  onRemove,
}: {
  attachment: Attachment;
  onRemove?: () => void;
}) {
  const isImage = attachment.kind === "image";
  return (
    <span
      className="inline-flex max-w-[12rem] items-center gap-1.5 rounded-md border border-white/[0.08] bg-black/25 px-2 py-1 text-[11px]"
      title={attachment.path ?? attachment.name}
    >
      {isImage && attachment.previewUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={attachment.previewUrl}
          alt={attachment.name}
          className="h-4 w-4 shrink-0 rounded object-cover"
        />
      ) : isImage ? (
        <ImageIcon className="h-3.5 w-3.5 shrink-0 text-violet-300/80" />
      ) : (
        <FileIcon className="h-3.5 w-3.5 shrink-0 text-amber-300/80" />
      )}
      <span className="min-w-0 flex-1 truncate">{attachment.name}</span>
      {attachment.size != null && (
        <span className="shrink-0 font-mono text-[9px] text-muted-foreground/50">
          {(attachment.size / 1024).toFixed(attachment.size < 1024 ? 0 : 1)}K
        </span>
      )}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:bg-white/10 hover:text-foreground"
          aria-label={`Remove ${attachment.name}`}
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </span>
  );
}

function ProcessingPing() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      className="rounded-xl glass p-4 glow-blue"
    >
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Bot size={16} className="text-blue-400" />
        <span>Работаю…</span>
        <span className="ml-2 inline-flex gap-1">
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-blue-400"
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.18 }}
            />
          ))}
        </span>
      </div>
    </motion.div>
  );
}
