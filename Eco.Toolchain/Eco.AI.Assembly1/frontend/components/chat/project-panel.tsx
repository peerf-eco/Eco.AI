"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  FolderClosed,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ProjectInfo, SessionInfo, SessionStatus } from "./types";
import { EcoosLogo } from "./ecoos-logo";

interface ProjectsPanelProps {
  open: boolean;
  onToggle: () => void;
  projects: ProjectInfo[];
  activeProjectId: string | null;
  onSelect: (project: ProjectInfo) => void;
  onNewProject: () => void;
}

// ────────────────────────────────────────────────────────────────────────────
// Left vertical panel: project list + per-project coding sessions.
// Collapses to an icon rail; selection highlights the current project card,
// past projects stay gray; clicking a card reveals its sessions.
// ────────────────────────────────────────────────────────────────────────────

export function ProjectsPanel({
  open,
  onToggle,
  projects,
  activeProjectId,
  onSelect,
  onNewProject,
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
        <button
          type="button"
          onClick={onToggle}
          title="Collapse panel"
          className="rounded-md p-1.5 text-muted-foreground hover:bg-white/[0.06] hover:text-foreground transition-colors"
        >
          <PanelLeftClose className="h-4 w-4" />
        </button>
      </div>

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
            <div key={project.id}>
              <button
                type="button"
                onClick={() => onSelect(project)}
                title={`${project.name}\n${project.path}`}
                className={cn(
                  "group flex w-full items-start gap-2.5 rounded-xl border px-3 py-2.5",
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
                      : "bg-white/[0.04] text-muted-foreground group-hover:text-foreground",
                  )}
                >
                  <FolderClosed className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div
                    className={cn(
                      "truncate text-xs font-medium",
                      active ? "text-foreground" : "text-muted-foreground",
                    )}
                  >
                    {project.name}
                  </div>
                  <div className="mt-0.5 truncate font-mono text-[10px] text-muted-foreground/50">
                    {project.path}
                  </div>
                </div>
                <span
                  className={cn(
                    "mt-1 h-1.5 w-1.5 shrink-0 rounded-full",
                    active
                      ? "bg-blue-400 shadow-[0_0_6px_rgba(96,165,250,0.6)]"
                      : "bg-zinc-600",
                  )}
                />
              </button>

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
                    <SessionRow key={session.id} session={session} />
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

function SessionRow({ session }: { session: SessionInfo }) {
  return (
    <div
      className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-white/[0.04] transition-colors"
      title={`${session.title}\nthread ${session.thread_id}`}
    >
      <StatusDot status={session.status} />
      <span className="min-w-0 flex-1 truncate text-[11px] text-foreground/70">
        {session.title || "(untitled)"}
      </span>
      <span className="shrink-0 text-[9px] uppercase tracking-wide text-muted-foreground/50">
        {relativeTime(session.updated_at)}
      </span>
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
