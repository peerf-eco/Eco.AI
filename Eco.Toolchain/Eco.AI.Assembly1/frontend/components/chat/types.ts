// ACOM pipeline UI types.
// Mirrors backend events from /ws/chat.
//
// Architectural idea borrowed from F:\ai-mek\repos\mek-ai-client\src\chat\types.ts:
// each assistant message is a list of typed Blocks. A pipeline run unfolds
// into a chain of blocks (phase header → tool/node card → optional plan-review
// or escalation form → final summary). Adding a new event type means adding a
// new Block.type variant — no global refactor.

// ────────────────────────────────────────────────────────────────────────────
// Chat phases emitted by the backend event contract.
// ────────────────────────────────────────────────────────────────────────────

export type HarnessPhase =
  | "planning"
  | "awaiting_approval"
  | "setup"
  | "coding"
  | "building"
  | "testing"
  | "review"
  | "failed_escalated"
  | "done";

export type PipelineNode =
  | "planner"
  | "plan_gate"
  | "setup"
  | "coder"
  | "builder"
  | "tester"
  | "reviewer"
  | "escalate";

// Stepper steps are dynamic per working mode — see stepperStepsForMode().

export const PHASE_LABEL: Record<HarnessPhase, string> = {
  planning: "Planning",
  awaiting_approval: "Awaiting approval",
  setup: "Setup",
  coding: "Coding",
  building: "Building",
  testing: "Testing",
  review: "Review",
  failed_escalated: "Escalated",
  done: "Done",
};

// One stepper step: a pipeline phase (or the terminal "done" marker) + label.
export interface StepperStep {
  phase: HarnessPhase;
  label: string;
}

// Token accounting for one pipeline phase / the whole session.
export interface TokenStat {
  input: number;
  output: number;
  total: number;
}

// Tokens consumed per pipeline phase (usage events bucketed server-side).
export type PhaseTokenMap = Partial<Record<HarnessPhase, TokenStat>>;

// Steps shown in the top progress bar, per working mode:
// - auto / migrate run the full plan→implement→verify pipeline;
// - single-phase modes (plan / code / test / review) run exactly one agent,
//   so the bar collapses to "1 — <step name>" and "2 — End".
export function stepperStepsForMode(mode: WorkingMode): StepperStep[] {
  switch (mode) {
    case "plan":
      return [
        { phase: "planning", label: "Plan" },
        { phase: "done", label: "End" },
      ];
    case "code":
      return [
        { phase: "coding", label: "Code" },
        { phase: "done", label: "End" },
      ];
    case "test":
      return [
        { phase: "testing", label: "Test" },
        { phase: "done", label: "End" },
      ];
    case "review":
      return [
        { phase: "review", label: "Review" },
        { phase: "done", label: "End" },
      ];
    case "migrate":
    case "auto":
    default:
      return [
        { phase: "planning", label: "Planning" },
        { phase: "coding", label: "Coding" },
        { phase: "testing", label: "Testing" },
        { phase: "done", label: "End" },
      ];
  }
}

// First phase a mode's pipeline enters — used to highlight the bar as soon
// as the user sends a request (before the first phase_change arrives).
export function initialPhaseForMode(mode: WorkingMode | undefined): HarnessPhase {
  switch (mode) {
    case "code": return "coding";
    case "test": return "testing";
    case "review": return "review";
    case "plan":
    case "migrate":
    case "auto":
    default: return "planning";
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Plan / component DTOs (from planner.submit_plan stop tool)
// ────────────────────────────────────────────────────────────────────────────

export interface PlanComponent {
  cid: string;
  version: string;
  name: string;
  reason: string;
}

// ────────────────────────────────────────────────────────────────────────────
// Block discriminated union — one ChatMessage carries blocks: Block[]
// ────────────────────────────────────────────────────────────────────────────

export type BlockId = string;

interface BlockBase {
  id: BlockId;
}

export interface TextBlock extends BlockBase {
  type: "text";
  content: string;       // Markdown
}

export interface PhaseHeaderBlock extends BlockBase {
  type: "phase_header";
  phase: HarnessPhase;
  node: PipelineNode | "";
}

export interface NodeDoneBlock extends BlockBase {
  type: "node_done";
  node: PipelineNode;
  // Free-form details. Renderer picks per-node payload.
  projectName?: string;
  componentsCount?: number;
  downloadedPaths?: string[];
  summaryMd?: string;
  buildArtifact?: string;
  reasonMd?: string;
}

export interface ToolCallBlock extends BlockBase {
  type: "tool_call";
  node: PipelineNode;
  toolName: string;
  args: Record<string, unknown>;
  status: "running" | "ok" | "error";
  output?: string;        // populated on tool_call_end if details has stringifiable shape
  durationMs?: number;
  startedAt: number;      // performance.now() / Date.now()
  // True when the call was rejected by a hardcoded policy gate (subcommand
  // whitelist, path allowlist, tool gate) rather than failing organically.
  blockedByPolicy?: boolean;
  denialReason?: string;
}

// Streaming thinking/reasoning text from the LLM. One block per ReAct
// iteration (a new tool_call_start finalises the current one). Only vendor
// reasoning channels (thinking_delta) stream into this block so it stays
// purely "how the model reasoned" — visible answers go to AnswerBlock.
export interface ThinkingBlock extends BlockBase {
  type: "thinking";
  node: PipelineNode;
  content: string;
  isActive: boolean;        // false → block collapses, caret hides
  startedAt: number;
}

// The model's visible answer (text_delta): always expanded, normal prose
// styling, never collapsed into a reasoning caret block. Finalised like
// thinking on tool/phase boundaries but the UI keeps it open regardless.
export interface AnswerBlock extends BlockBase {
  type: "answer";
  node: PipelineNode;
  content: string;
  isActive: boolean;        // controls the live caret only — never collapses
  startedAt: number;
}

export interface FailBlock extends BlockBase {
  type: "build_fail" | "test_fail";
  message: string;       // error_md or reason_md, Markdown-ish
  retryCount: number;
}

export interface PlanReviewBlock extends BlockBase {
  type: "plan_review";
  planMd: string;
  components: PlanComponent[];
  projectName: string;
  // Once user decides, we freeze the block: status non-null.
  status: null | "approved" | "rejected";
}

export interface EscalationBlock extends BlockBase {
  type: "escalation";
  reason: string;
  failureOrigin: string;
  retryCount: number;
  maxRetries: number;
  buildLog: string;
  testerReportMd: string;
  planMd: string;
  coderSummaryMd: string;
  status: null | "continue" | "abort";
}

export interface PipelineDoneBlock extends BlockBase {
  type: "pipeline_done";
  status: string;        // "success" | "user_aborted" | other backend value
  buildArtifact: string;
  testerReportMd: string;
}

export interface ErrorBlock extends BlockBase {
  type: "error";
  content: string;
}

export type Block =
  | TextBlock
  | PhaseHeaderBlock
  | NodeDoneBlock
  | ToolCallBlock
  | ThinkingBlock
  | AnswerBlock
  | FailBlock
  | PlanReviewBlock
  | EscalationBlock
  | PipelineDoneBlock
  | ErrorBlock;

// ────────────────────────────────────────────────────────────────────────────
// ChatMessage — what the UI list renders
// ────────────────────────────────────────────────────────────────────────────

export type MessageRole = "user" | "assistant";

// ────────────────────────────────────────────────────────────────────────────
// Attachments — session-scoped files the user pins to every message.
// ────────────────────────────────────────────────────────────────────────────

export type AttachmentKind = "text" | "image";

export interface Attachment {
  id: string;                 // crypto.randomUUID()
  name: string;              // display name / file name
  path?: string;             // absolute path (mention / picker); absent for paste
  kind: AttachmentKind;
  mime?: string;
  size?: number;
  content?: string;          // pasted payload (base64 data URL for images, or text)
  previewUrl?: string;       // object URL for image thumbnail in chip
  source: "mention" | "picker" | "paste" | "drop";
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  // User messages use this; assistant messages aggregate blocks.
  text?: string;
  blocks: Block[];
  attachments?: Attachment[];
}

// ────────────────────────────────────────────────────────────────────────────
// Server events (matches backend/server.py emit_updates + interrupt handling)
// ────────────────────────────────────────────────────────────────────────────

interface ServerEventBase {
  type: string;
}

export interface HeartbeatEvent extends ServerEventBase {
  type: "heartbeat";
  protocol?: string;
  thread_id?: string;
}

export interface WorktreeCreatedEvent extends ServerEventBase {
  type: "worktree_created";
  path: string;
  name: string;
}

export interface PhaseChangeEvent extends ServerEventBase {
  type: "phase_change";
  phase: HarnessPhase;
  node: PipelineNode;
}

export interface NodeDoneEvent extends ServerEventBase {
  type: "node_done";
  node: PipelineNode;
  project_name?: string;
  components_count?: number;
  downloaded_paths?: string[];
  summary_md?: string;
  build_artifact?: string;
  reason_md?: string;
}

export interface BuildFailEvent extends ServerEventBase {
  type: "build_fail";
  error_md: string;
  retry_count: number;
}

export interface TestFailEvent extends ServerEventBase {
  type: "test_fail";
  reason_md: string;
  retry_count: number;
}

export interface PlanReviewRequiredEvent extends ServerEventBase {
  type: "plan_review_required";
  plan_md: string;
  components: PlanComponent[];
  project_name: string;
}

export type NodeEventKind =
  | "start"
  | "text_delta"
  | "thinking_delta"
  | "tool_call_start"
  | "tool_call_end"
  | "tool_update"
  | "iteration"
  | "done"
  | "no_tool_call"
  | "max_iters"
  | "error";

export interface NodeEventEvent extends ServerEventBase {
  type: "node_event";
  node: PipelineNode;
  event: NodeEventKind;
  data: {
    // tool_call_start
    name?: string;
    args?: Record<string, unknown>;
    // tool_call_end
    is_error?: boolean;
    // Policy denial marker / failure preview forwarded inside details by the
    // agent loop (denied: subcommand-whitelist or path-gate rejection).
    details?: Record<string, unknown> | null;
    // iteration
    i?: number;
    // error / max_iters
    reason?: string;
    // stop_tool / payload (done)
    stop_tool?: string;
    payload?: Record<string, unknown>;
    // text_delta / thinking_delta — one token-ish slice of LLM output.
    content?: string;
  };
}

export interface EscalationRequiredEvent extends ServerEventBase {
  type: "escalation_required";
  reason: string;
  failure_origin: string;
  retry_count: number;
  max_retries: number;
  build_log: string;
  tester_report_md: string;
  plan_md: string;
  coder_summary_md: string;
}

export interface PipelineDoneEvent extends ServerEventBase {
  type: "pipeline_done";
  status: string;
  build_artifact: string;
  tester_report_md: string;
}

// Per-LLM-call token accounting, bucketed by the pipeline phase that was
// running when the call completed. Drives the phase stepper counters.
export interface UsageEvent extends ServerEventBase {
  type: "usage";
  node: PipelineNode;
  phase: HarnessPhase;
  usage: {
    input: number;
    output: number;
    cache_read: number;
    cache_write: number;
    total: number;
  };
}

export interface ErrorEvent extends ServerEventBase {
  type: "error";
  content: string;
}

export type ServerEvent =
  | HeartbeatEvent
  | WorktreeCreatedEvent
  | PhaseChangeEvent
  | NodeDoneEvent
  | NodeEventEvent
  | BuildFailEvent
  | TestFailEvent
  | PlanReviewRequiredEvent
  | EscalationRequiredEvent
  | PipelineDoneEvent
  | UsageEvent
  | ErrorEvent;

// ────────────────────────────────────────────────────────────────────────────
// Client messages (what we send to backend)
// ────────────────────────────────────────────────────────────────────────────

export interface UserRequestMessage {
  type: "user_request";
  user_request: string;
  project_dir?: string;
  max_retries?: number;
  // Target component platform: which marketplace files to download and
  // which BuildFiles/<OS>/<arch>/ subdir to point the build at. Defaults
  // (Linux/x86_64) live in .env if these are omitted.
  target_os?: string;
  target_arch?: string;
  language?: string;
  mode?: WorkingMode;
  use_worktree?: boolean;
  // Session-scoped user attachments (see Attachment). Sent on every request.
  attached_files?: Array<{
    name: string;
    path?: string;
    kind: AttachmentKind;
    mime?: string;
    size?: number;
    content?: string;   // for paste-only attachments (no path)
  }>;
}

export type WorkingMode = "auto" | "plan" | "code" | "migrate" | "test" | "review";

export interface PlanDecisionMessage {
  type: "plan_decision";
  approved: boolean;
  modified_plan_md?: string;
  reason?: string;
}

export interface EscalationDecisionMessage {
  type: "escalation_decision";
  continue: boolean;
}

export interface AbortMessage {
  type: "abort";
}

export type ClientMessage =
  | UserRequestMessage
  | PlanDecisionMessage
  | EscalationDecisionMessage
  | AbortMessage;

// ────────────────────────────────────────────────────────────────────────────
// Projects panel DTOs (GET/POST /api/projects, GET /api/fs/browse)
// ────────────────────────────────────────────────────────────────────────────

export type SessionStatus = "running" | "success" | "failed" | "aborted" | "idle";

export interface SessionInfo {
  id: string;
  thread_id: string;
  project_path: string;
  title: string;
  created_at: string;
  updated_at: string;
  status: SessionStatus;
  // Optional trace-bookkeeping fields (returned by /api/sessions/{id}/trace
  // and surfaced on /api/sessions/{id}/messages since the ses- prefix
  // minimal-first-cut). All optional so older payloads keep parsing.
  trace_dir?: string;
  trace_last_file?: string | null;
  trace_last_error?: string | null;
  trace_call_count?: number;
}

export interface ProjectInfo {
  id: string;
  path: string;
  name: string;
  added_at: string;
  auto?: boolean;
  sessions: SessionInfo[];
}

export interface FsEntry {
  name: string;
  path: string;
  type: "dir" | "file";
  size?: number;
}

export interface FsListing {
  path: string;
  parent: string | null;
  entries: FsEntry[];
}
