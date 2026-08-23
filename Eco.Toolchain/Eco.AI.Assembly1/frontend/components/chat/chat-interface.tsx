"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send, Bot, User, Settings, X, Sparkles, StopCircle, RotateCcw,
  GitBranch, Workflow,
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
import { ProjectsPanel } from "./project-panel";
import { FolderBrowser } from "./folder-browser";
import { EcoosLogo } from "./ecoos-logo";
import { AgentSettings } from "./agent-settings";
import { RagImport } from "./rag-import";
import type { ChatMessage, ProjectInfo, WorkingMode } from "./types";

const PLATFORM_STORAGE_KEY = "eco_harness.target_platform";
const LANGUAGE_STORAGE_KEY = "eco_harness.language";
const PANEL_OPEN_STORAGE_KEY = "eco_harness.panel_open";
const ACTIVE_PROJECT_STORAGE_KEY = "eco_harness.active_project";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";
const WS_BASE = API_URL.replace(/^http/, "ws");

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
    sendUserRequest(input, {
      targetOs: platform.os,
      targetArch: platform.arch,
      language,
      mode,
      useWorktree,
      projectDir: activeProject?.path,
    });
    setInput("");
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
              className="fixed inset-y-0 right-0 z-50 w-80 glass-strong p-5 shadow-2xl overflow-y-auto thin-scroll"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-gradient">Settings</h2>
                <Button variant="ghost" size="icon" onClick={() => setShowSettings(false)} className="hover:bg-white/10">
                  <X className="h-4 w-4" />
                </Button>
              </div>
              {threadId && (
                <div className="mt-6 pt-4 border-t border-white/[0.06] text-xs text-muted-foreground">
                  <div className="uppercase tracking-wide text-[10px] mb-1">Thread</div>
                  <div className="font-mono text-foreground/80 break-all">{threadId}</div>
                </div>
              )}
              <div className="mt-6 pt-4 border-t border-white/[0.06] space-y-5">
                <div>
                  <div className="uppercase tracking-wide text-[10px] mb-2 text-muted-foreground">Agent configuration</div>
                  <AgentSettings />
                </div>
                <div className="border-t border-white/[0.06] pt-4">
                  <div className="uppercase tracking-wide text-[10px] mb-2 text-muted-foreground">Marketplace RAG</div>
                  <RagImport />
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Folder browser */}
      <AnimatePresence>
        {browserOpen && (
          <FolderBrowser onClose={() => setBrowserOpen(false)} onAdded={handleProjectAdded} />
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
                size="icon"
                onClick={clearMessages}
                className="hover:bg-white/10 rounded-lg"
                title="New session"
              >
                <RotateCcw className="h-4 w-4" />
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
            <div className="rounded-2xl glass-strong shadow-2xl transition-colors focus-within:border-blue-500/30 focus-within:glow-blue border border-transparent">
              <textarea
                ref={scrollAnchorRef}
                rows={1}
                placeholder="Type a message…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault();
                    onSend();
                  }
                }}
                disabled={!isConnected || isProcessing}
                className="block w-full resize-none bg-transparent px-4 pb-1 pt-3.5 text-sm outline-none placeholder:text-muted-foreground/60 disabled:opacity-50"
              />
              <div className="flex items-center gap-1.5 px-2 pb-2 pt-1.5">
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
        </div>
      </div>
    </motion.div>
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
