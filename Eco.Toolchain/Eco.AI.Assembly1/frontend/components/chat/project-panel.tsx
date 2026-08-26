"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Download,
  FileText,
  FolderClosed,
  FolderDown,
  MoreVertical,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  StopCircle,
  Trash2,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ProjectInfo, SessionInfo, SessionStatus } from "./types";
import { EcoosLogo } from "./ecoos-logo";

export type ExportFormat = "jsonl" | "txt";

interface ProjectsPanelProps {
  open: boolean;
  onToggle: () => void;
  projects: ProjectInfo[];
  activeProjectId: string | null;
  onSelect: (project: ProjectInfo) => void;
  onNewProject: () => void;
  onRemoveProject?: (project: ProjectInfo) => void;
  onExportProject?: (project: ProjectInfo, format: ExportFormat) => void;
  onExportAll?: (format: ExportFormat) => void;
  // Open a session's transcript in the main view.
  onSelectSession?: (session: SessionInfo) => void;
  // Stop a running/suspended session (backend abort).
  onStopSession?: (session: SessionInfo) => void;
  // Currently opened session (highlighted in the list).
  activeSessionId?: string | null;
  exportBusy?: boolean;
  notice?: string | null;
  onDismissNotice?: () => void;
}

// ────────────────────────────────────────────────────────────────────────────
// Left vertical panel: whitelisted projects + per-project coding sessions.
// Collapses to an icon rail; selection highlights the current project card,
// past projects stay gray; clicking a card reveals its sessions. Each card
// carries a 3-dot menu (session export / remove from panel); the panel
// header offers combined export of all projects.
// ────────────────────────────────────────────────────────────────────────────

export function ProjectsPanel({
  open,
  onToggle,
  projects,
  activeProjectId,
  onSelect,
  onNewProject,
  onRemoveProject,
  onExportProject,
  onExportAll,
  onSelectSession,
  onStopSession,
  activeSessionId,
  exportBusy = false,
  notice,
  onDismissNotice,
}: ProjectsPanelProps) {
  // Which card's session list is unfolded — follows selection by default.
  const [expandedId, setExpandedId] = useState<string | null>(activeProjectId);
  useEffect(() => {
    if (activeProjectId) setExpandedId(activeProjectId);
  }, [activeProjectId]);

  if (!open) {
    return (
      <aside className="relative z-20 flex h-full w-[60px] shrink-0 flex-col items-center gap-2 border-r border-white/[0.06] glass py-4">
        <EcoosLogo className="mb-2 h-9 w-9" />
        <RailButton label="Expand projects panel" onClick={onToggle}>
          <PanelLeftOpen className="h-4 w-4" />
        </RailButton>
        <RailButton label="Add project" onClick={onNewProject}>
          <Plus className="h-4 w-4" />
        </RailButton>
        <div className="mt-1 flex flex-col items-center gap-1.5">
          {projects.slice(0, 6).map((p) => (
            <button
              key={p.id}
              type="button"
              title={p.name}
              onClick={() => onSelect(p)}
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-lg border transition-colors",
                p.id === activeProjectId
                  ? "border-blue-500/40 bg-blue-500/15 text-blue-300"
                  : "border-white/[0.06] bg-white/[0.03] text-muted-foreground hover:text-foreground",
              )}
            >
              <FolderClosed className="h-3.5 w-3.5" />
            </button>
          ))}
        </div>
      </aside>
    );
  }

  return (
    <motion.aside
      initial={{ width: 60 }}
      animate={{ width: 272 }}
      exit={{ width: 60 }}
      transition={{ type: "spring", damping: 28, stiffness: 260 }}
      className="relative z-20 flex h-full shrink-0 flex-col border-r border-white/[0.06] glass overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <EcoosLogo className="h-8 w-8 shrink-0" />
          <span className="truncate text-sm font-semibold tracking-tight">Projects</span>
        </div>
        <div className="flex shrink-0 items-center gap-0.5">
          <PanelMenu exportBusy={exportBusy} onExportAll={onExportAll} />
          <button
            type="button"
            onClick={onToggle}
            title="Collapse panel"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-white/[0.06] hover:text-foreground transition-colors"
          >
            <PanelLeftClose className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Transient notice (removal blocked, export errors, …) */}
      {notice && (
        <div className="mx-3 mb-2 flex items-start gap-2 rounded-lg border border-white/[0.08] bg-black/25 px-2.5 py-2 text-[11px] leading-snug text-muted-foreground">
          <span className="min-w-0 flex-1 break-words">{notice}</span>
          {onDismissNotice && (
            <button
              type="button"
              onClick={onDismissNotice}
              aria-label="Dismiss"
              className="shrink-0 rounded p-0.5 text-muted-foreground/70 transition-colors hover:bg-white/10 hover:text-foreground"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
      )}

      {/* New project */}
      <div className="px-3 pb-3">
        <button
          type="button"
          onClick={onNewProject}
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded-xl border border-dashed",
            "border-white/[0.14] bg-white/[0.02] px-3 py-2.5",
            "text-xs font-medium text-muted-foreground",
            "hover:border-blue-500/40 hover:bg-blue-500/[0.06] hover:text-blue-200",
            "transition-colors",
          )}
        >
          <Plus className="h-3.5 w-3.5" />
          New Project
        </button>
      </div>

      {/* Project cards */}
      <div className="flex-1 space-y-1.5 overflow-y-auto px-3 pb-4 thin-scroll">
        {projects.length === 0 && (
          <p className="px-2 pt-6 text-center text-xs leading-relaxed text-muted-foreground/70">
            No projects yet.
            <br />
            Add a folder to start building in it.
          </p>
        )}
        {projects.map((project) => {
          const active = project.id === activeProjectId;
          const expanded = project.id === expandedId && project.sessions.length > 0;
          return (
            <div key={project.id} className="relative group/card">
              <button
                type="button"
                onClick={() => onSelect(project)}
                title={`${project.name}\n${project.path}`}
                className={cn(
                  "flex w-full items-start gap-2.5 rounded-xl border px-3 py-2.5",
                  "text-left transition-colors",
                  active
                    ? "border-blue-500/40 bg-blue-500/[0.08]"
                    : "border-white/[0.05] bg-white/[0.02]",
                  !active && "hover:bg-white/[0.05]",
                )}
              >
                <div
                  className={cn(
                    "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg",
                    active
                      ? "bg-gradient-to-br from-blue-500/30 to-violet-500/30 text-blue-200"
                      : "bg-white/[0.04] text-muted-foreground group-hover/card:text-foreground",
                  )}
                >
                  <FolderClosed className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0 flex-1 pr-4">
                  <div className="flex min-w-0 items-center gap-1.5">
                    <ProjectStatusDot project={project} selected={active} />
                    <div
                      className={cn(
                        "truncate text-xs font-medium",
                        active ? "text-foreground" : "text-muted-foreground",
                      )}
                    >
                      {project.name}
                    </div>
                  </div>
                  <div className="mt-0.5 truncate font-mono text-[10px] text-muted-foreground/50">
                    {project.path}
                  </div>
                </div>
              </button>

              <ProjectCardMenu
                project={project}
                active={active}
                onExport={(format) => onExportProject?.(project, format)}
                onRemove={() => onRemoveProject?.(project)}
              />

              {/* Sessions revealed under the selected project */}
              {expanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.18, ease: "easeOut" }}
                  className="ml-5 mt-1 space-y-0.5 overflow-hidden border-l border-white/[0.06] pl-3"
                >
                  {project.sessions.map((session) => (
                    <SessionRow
                      key={session.id}
                      session={session}
                      active={session.id === activeSessionId}
                      onSelect={onSelectSession}
                      onStop={onStopSession}
                    />
                  ))}
                </motion.div>
              )}
            </div>
          );
        })}
      </div>
    </motion.aside>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Card 3-dot menu: session export + remove-from-panel (visual only).
// ────────────────────────────────────────────────────────────────────────────

const REMOVE_BLOCKED_TITLE = "Cannot remove a project with a running session";
const REMOVE_TITLE = "Projects can be re-added anytime; nothing is deleted";

function useDismissable(open: boolean, close: () => void) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onMouseDown = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        close();
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, close]);
  return wrapperRef;
}

function ProjectCardMenu({
  project,
  active,
  onExport,
  onRemove,
}: {
  project: ProjectInfo;
  active: boolean;
  onExport: (format: ExportFormat) => void;
  onRemove: () => void;
}) {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  const wrapperRef = useDismissable(open, close);
  const removeBlocked = project.sessions.some((s) => s.status === "running");

  return (
    <div ref={wrapperRef} className="absolute right-1.5 top-1.5 z-10">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        title={removeBlocked ? REMOVE_BLOCKED_TITLE : "Project actions"}
        onClick={(e) => {
          e.stopPropagation();
          if (removeBlocked) return;
          setOpen((v) => !v);
        }}
        className={cn(
          "rounded-md p-1 text-muted-foreground transition-opacity",
          "hover:bg-white/10 hover:text-foreground",
          "bg-black/40 opacity-0 backdrop-blur-sm",
          "focus:opacity-100 group-hover/card:opacity-100",
          open && "opacity-100",
          removeBlocked &&
            "cursor-not-allowed opacity-40 hover:bg-transparent hover:text-muted-foreground",
        )}
      >
        <MoreVertical className="h-3.5 w-3.5" />
      </button>
      {open && (
        <div
          role="menu"
          className={cn(
            "absolute right-0 top-full mt-1 z-50 min-w-[176px]",
            "rounded-xl border border-white/10 glass-strong",
            "shadow-[0_16px_48px_-12px_rgba(0,0,0,0.8)] p-1.5 space-y-0.5",
          )}
        >
          <MenuItem
            icon={<Download className="h-3.5 w-3.5 text-blue-300/90" />}
            label="Export sessions · JSONL"
            onClick={() => {
              close();
              onExport("jsonl");
            }}
          />
          <MenuItem
            icon={<FileText className="h-3.5 w-3.5 text-blue-300/90" />}
            label="Export sessions · TXT"
            onClick={() => {
              close();
              onExport("txt");
            }}
          />
          <div className="my-1 h-px bg-white/[0.08]" role="separator" />
          <MenuItem
            danger
            icon={<Trash2 className="h-3.5 w-3.5" />}
            label="Remove from panel"
            title={REMOVE_TITLE}
            onClick={() => {
              close();
              onRemove();
            }}
          />
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Header export-all menu.
// ────────────────────────────────────────────────────────────────────────────

function PanelMenu({
  exportBusy,
  onExportAll,
}: {
  exportBusy: boolean;
  onExportAll?: (format: ExportFormat) => void;
}) {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  const wrapperRef = useDismissable(open, close);

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={exportBusy}
        title="Export all projects' sessions"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "rounded-md p-1.5 text-muted-foreground transition-colors",
          "hover:bg-white/[0.06] hover:text-foreground",
          open && "bg-white/[0.06] text-foreground",
          exportBusy && "cursor-not-allowed opacity-40",
        )}
      >
        <FolderDown className="h-4 w-4" />
      </button>
      {open && (
        <div
          role="menu"
          className={cn(
            "absolute right-0 top-full mt-1 z-50 min-w-[196px]",
            "rounded-xl border border-white/10 glass-strong",
            "shadow-[0_16px_48px_-12px_rgba(0,0,0,0.8)] p-1.5 space-y-0.5",
          )}
        >
          <MenuItem
            icon={<Download className="h-3.5 w-3.5 text-blue-300/90" />}
            label="Export all projects · JSONL"
            onClick={() => {
              close();
              onExportAll?.("jsonl");
            }}
          />
          <MenuItem
            icon={<FileText className="h-3.5 w-3.5 text-blue-300/90" />}
            label="Export all projects · TXT"
            onClick={() => {
              close();
              onExportAll?.("txt");
            }}
          />
        </div>
      )}
    </div>
  );
}

function MenuItem({
  icon,
  label,
  onClick,
  danger,
  title,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  danger?: boolean;
  title?: string;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      title={title ?? label}
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5",
        "text-left text-xs transition-colors",
        danger
          ? "text-red-300 hover:bg-red-500/15"
          : "text-white hover:bg-white/10",
      )}
    >
      {icon}
      <span className="truncate">{label}</span>
    </button>
  );
}

function RailButton({
  children,
  label,
  onClick,
}: {
  children: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-foreground"
    >
      {children}
    </button>
  );
}

function SessionRow({
  session,
  active,
  onSelect,
  onStop,
}: {
  session: SessionInfo;
  active?: boolean;
  onSelect?: (session: SessionInfo) => void;
  onStop?: (session: SessionInfo) => void;
}) {
  const running = session.status === "running";
  return (
    <div
      className={cn(
        "group/session flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors",
        active ? "bg-blue-500/[0.10]" : "hover:bg-white/[0.04]",
      )}
      title={`${session.title}\nthread ${session.thread_id}`}
    >
      <button
        type="button"
        onClick={() => onSelect?.(session)}
        className="flex min-w-0 flex-1 items-center gap-2 text-left"
      >
        <StatusDot status={session.status} />
        <span className="min-w-0 flex-1 truncate text-[11px] text-foreground/70">
          {session.title || "(untitled)"}
        </span>
        <span className="shrink-0 text-[9px] uppercase tracking-wide text-muted-foreground/50">
          {relativeTime(session.updated_at)}
        </span>
      </button>
      {running && onStop && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onStop(session);
          }}
          title="Stop this session"
          aria-label="Stop session"
          className="shrink-0 rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-red-500/10 hover:text-red-400 group-hover/session:opacity-100"
        >
          <StopCircle className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}

function StatusDot({ status }: { status: SessionStatus }) {
  const cls: Record<SessionStatus, string> = {
    running: "bg-blue-400 animate-pulse shadow-[0_0_6px_rgba(96,165,250,0.6)]",
    success: "bg-emerald-400",
    failed: "bg-red-400",
    aborted: "bg-amber-400",
    idle: "bg-zinc-500",
  };
  return <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", cls[status])} />;
}

// ────────────────────────────────────────────────────────────────────────────
// Project-card status light (left of the project name). Precedence:
// selected > has running sessions > has suspended session > idle only.
// ────────────────────────────────────────────────────────────────────────────

function ProjectStatusDot({
  project,
  selected,
}: {
  project: ProjectInfo;
  selected: boolean;
}) {
  const hasRunning = project.sessions.some((s) => s.status === "running");
  const hasSuspended = project.sessions.some((s) => s.status === "aborted");
  const cls = selected
    ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]"
    : hasRunning
      ? "bg-blue-400 shadow-[0_0_6px_rgba(96,165,250,0.6)]"
      : hasSuspended
        ? "bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.45)]"
        : "bg-zinc-600";
  const label = selected
    ? "Selected project"
    : hasRunning
      ? "Has active sessions"
      : hasSuspended
        ? "Has suspended session"
        : "Inactive sessions only";
  return (
    <span
      className={cn("h-1.5 w-1.5 shrink-0 rounded-full", cls)}
      title={label}
      aria-label={label}
      role="img"
    />
  );
}

function relativeTime(iso: string): string {
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return "";
  const diff = Date.now() - ts;
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "now";
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d`;
  return `${Math.floor(days / 30)}mo`;
}
