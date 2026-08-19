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
  | "failed_escalated"
  | "done";

export type PipelineNode =
  | "planner"
  | "plan_gate"
  | "setup"
  | "coder"
  | "builder"
  | "tester"
  | "escalate";

// 5 stages visible in the top stepper. "failed_escalated" is not a stage,
// it surfaces as an Escalation block inside the message stream.
export const STEPPER_PHASES: HarnessPhase[] = ["planning", "setup", "coding", "building", "testing"];

export const PHASE_LABEL: Record<HarnessPhase, string> = {
  planning: "Planning",
  awaiting_approval: "Awaiting approval",
  setup: "Setup",
  coding: "Coding",
  building: "Building",
  testing: "Testing",
  failed_escalated: "Escalated",
  done: "Done",
};

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
}

// Streaming thinking/reasoning text from the LLM. One block per ReAct
// iteration (a new tool_call_start finalises the current one). Both vendor
// reasoning channels (additional_kwargs.reasoning_content) and visible
// content tokens stream into this block so the user sees the model "work"
// regardless of whether the underlying model is in thinking mode.
export interface ThinkingBlock extends BlockBase {
  type: "thinking";
  node: PipelineNode;
  content: string;
  isActive: boolean;        // false → block collapses, caret hides
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
  | FailBlock
  | PlanReviewBlock
  | EscalationBlock
  | PipelineDoneBlock
  | ErrorBlock;

// ────────────────────────────────────────────────────────────────────────────
// ChatMessage — what the UI list renders
// ────────────────────────────────────────────────────────────────────────────

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  // User messages use this; assistant messages aggregate blocks.
  text?: string;
  blocks: Block[];
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

export interface ErrorEvent extends ServerEventBase {
  type: "error";
  content: string;
}

export type ServerEvent =
  | HeartbeatEvent
  | PhaseChangeEvent
  | NodeDoneEvent
  | NodeEventEvent
  | BuildFailEvent
  | TestFailEvent
  | PlanReviewRequiredEvent
  | EscalationRequiredEvent
  | PipelineDoneEvent
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
  worktree_name?: string;
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
