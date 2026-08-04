"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  Block,
  ChatMessage,
  ClientMessage,
  PipelineNode,
  ServerEvent,
  HarnessPhase,
} from "./types";

// ────────────────────────────────────────────────────────────────────────────
// id generation — UUID where available, counter as a safe fallback.
// ────────────────────────────────────────────────────────────────────────────
let _idCounter = 0;
function newId(prefix: string): string {
  _idCounter += 1;
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}_${crypto.randomUUID().slice(0, 8)}_${_idCounter}`;
  }
  return `${prefix}_${_idCounter}_${Math.random().toString(36).slice(2, 8)}`;
}

const THREAD_ID_KEY = "eco_harness.thread_id";

// Tool output preview cap — collapsible cards in the chat show only the
// first N chars; the full payload is available in dev tools / logs.
const TOOL_OUTPUT_PREVIEW_CHARS = 500;

function safeStringifyPreview(value: unknown): string | undefined {
  if (value === null || value === undefined) return undefined;
  try {
    return JSON.stringify(value).slice(0, TOOL_OUTPUT_PREVIEW_CHARS);
  } catch {
    // Circular refs, BigInt, etc. — never crash the chat UI for telemetry.
    return "[unserializable]";
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Pure helpers — append/update blocks immutably inside the message list.
// Same idea as mek-ai useChatStream.ts:30-65.
// ────────────────────────────────────────────────────────────────────────────

function appendBlock(prev: ChatMessage[], block: Block): ChatMessage[] {
  const last = prev[prev.length - 1];
  if (last && last.role === "assistant") {
    return [
      ...prev.slice(0, -1),
      { ...last, blocks: [...last.blocks, block] },
    ];
  }
  return [
    ...prev,
    { id: newId("msg"), role: "assistant", blocks: [block] },
  ];
}

function updateBlock(
  prev: ChatMessage[],
  predicate: (b: Block) => boolean,
  updater: (b: Block) => Block,
): ChatMessage[] {
  return prev.map((msg) => ({
    ...msg,
    blocks: msg.blocks.map((b) => (predicate(b) ? updater(b) : b)),
  }));
}

// Walk blocks tail-first, mutate the first match, return the new list. Same
// reverse-scan idea as mek-ai useChatStream.ts:49-65 — works because backend
// emits per-node events in order and we never need to update older blocks.
function updateLastBlock(
  prev: ChatMessage[],
  predicate: (b: Block) => boolean,
  updater: (b: Block) => Block,
): { messages: ChatMessage[]; matched: boolean } {
  let matched = false;
  const reversed = [...prev].reverse();
  const updated = reversed.map((msg) => {
    if (matched) return msg;
    const idxFromTail = [...msg.blocks].reverse().findIndex(predicate);
    if (idxFromTail === -1) return msg;
    const realIdx = msg.blocks.length - 1 - idxFromTail;
    matched = true;
    return {
      ...msg,
      blocks: msg.blocks.map((b, i) => (i === realIdx ? updater(b) : b)),
    };
  }).reverse();
  return { messages: updated, matched };
}

// Flip every active ThinkingBlock for `node` (or all nodes when undefined)
// to isActive=false so the UI collapses the caret/pulse without deleting
// the history. Called on tool_call_start, phase_change, pipeline_done — any
// boundary that semantically ends a reasoning burst.
function finalizeActiveThinking(prev: ChatMessage[], node?: PipelineNode): ChatMessage[] {
  return prev.map((msg) => ({
    ...msg,
    blocks: msg.blocks.map((b) =>
      b.type === "thinking" && b.isActive && (node === undefined || b.node === node)
        ? { ...b, isActive: false }
        : b,
    ),
  }));
}

// ────────────────────────────────────────────────────────────────────────────
// Compatibility module for the V7 chat UI.
// ────────────────────────────────────────────────────────────────────────────

export interface UseHarnessSocketResult {
  messages: ChatMessage[];
  isConnected: boolean;
  isProcessing: boolean;
  currentPhase: HarnessPhase | null;
  completedPhases: HarnessPhase[];
  threadId: string | null;

  sendUserRequest: (
    text: string,
    opts?: { projectDir?: string; maxRetries?: number; targetOs?: string; targetArch?: string; language?: string },
  ) => void;
  sendPlanDecision: (blockId: string, approved: boolean, opts?: { modifiedPlanMd?: string; reason?: string }) => void;
  sendEscalationDecision: (blockId: string, cont: boolean) => void;
  sendAbort: () => void;
  clearMessages: () => void;
}

export function useHarnessSocket(wsBaseUrl: string): UseHarnessSocketResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<HarnessPhase | null>(null);
  const [completedPhases, setCompletedPhases] = useState<HarnessPhase[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalClose = useRef(false);
  const handleEventRef = useRef<(ev: ServerEvent) => void>(() => {});

  // ── event handler ────────────────────────────────────────────────────────
  const handleEvent = useCallback((ev: ServerEvent) => {
    switch (ev.type) {
      case "heartbeat": {
        if (ev.thread_id) {
          setThreadId(ev.thread_id);
          if (typeof window !== "undefined") {
            sessionStorage.setItem(THREAD_ID_KEY, ev.thread_id);
          }
        }
        return;
      }

      case "phase_change": {
        setCurrentPhase((prevPhase) => {
          if (prevPhase && prevPhase !== ev.phase) {
            setCompletedPhases((p) => (p.includes(prevPhase) ? p : [...p, prevPhase]));
          }
          return ev.phase;
        });
        setMessages((prev) => {
          // Crossing a phase boundary means the previous node has stopped
          // reasoning — collapse all active thinking blocks first, then
          // append the phase header.
          const collapsed = finalizeActiveThinking(prev);
          return appendBlock(collapsed, {
            id: newId("phase"),
            type: "phase_header",
            phase: ev.phase,
            node: ev.node,
          });
        });
        return;
      }

      case "node_done": {
        setMessages((prev) => {
          const collapsed = finalizeActiveThinking(prev, ev.node as PipelineNode);
          return appendBlock(collapsed, {
            id: newId("nodedone"),
            type: "node_done",
            node: ev.node as PipelineNode,
            projectName: ev.project_name,
            componentsCount: ev.components_count,
            downloadedPaths: ev.downloaded_paths,
            summaryMd: ev.summary_md,
            buildArtifact: ev.build_artifact,
            reasonMd: ev.reason_md,
          });
        });
        return;
      }

      case "build_fail": {
        setMessages((prev) => appendBlock(prev, {
          id: newId("buildfail"),
          type: "build_fail",
          message: ev.error_md,
          retryCount: ev.retry_count,
        }));
        return;
      }

      case "test_fail": {
        setMessages((prev) => appendBlock(prev, {
          id: newId("testfail"),
          type: "test_fail",
          message: ev.reason_md,
          retryCount: ev.retry_count,
        }));
        return;
      }

      case "plan_review_required": {
        setIsProcessing(false);
        setMessages((prev) => appendBlock(prev, {
          id: newId("planreview"),
          type: "plan_review",
          planMd: ev.plan_md,
          components: ev.components || [],
          projectName: ev.project_name || "",
          status: null,
        }));
        return;
      }

      case "escalation_required": {
        setIsProcessing(false);
        setMessages((prev) => appendBlock(prev, {
          id: newId("escalation"),
          type: "escalation",
          reason: ev.reason || "unknown",
          failureOrigin: ev.failure_origin || "",
          retryCount: ev.retry_count || 0,
          maxRetries: ev.max_retries || 0,
          buildLog: ev.build_log || "",
          testerReportMd: ev.tester_report_md || "",
          planMd: ev.plan_md || "",
          coderSummaryMd: ev.coder_summary_md || "",
          status: null,
        }));
        return;
      }

      case "pipeline_done": {
        setIsProcessing(false);
        if (currentPhase) {
          setCompletedPhases((p) => (p.includes(currentPhase) ? p : [...p, currentPhase]));
        }
        setMessages((prev) => {
          const collapsed = finalizeActiveThinking(prev);
          return appendBlock(collapsed, {
            id: newId("done"),
            type: "pipeline_done",
            status: ev.status,
            buildArtifact: ev.build_artifact || "",
            testerReportMd: ev.tester_report_md || "",
          });
        });
        // Terminal state — drop the thread_id so the next user_request creates
        // a fresh thread. Backend graph would otherwise resume a "dead" thread
        // after page reload and reply with stale interrupts.
        if (typeof window !== "undefined") {
          sessionStorage.removeItem(THREAD_ID_KEY);
        }
        setThreadId(null);
        return;
      }

      case "node_event": {
        if (ev.event === "thinking_delta" || ev.event === "text_delta") {
          const delta = (ev.data.content as string | undefined) ?? "";
          if (!delta) return;
          // Append to the most-recent active thinking block of this node;
          // if none, start a new one. Inactive blocks (already finalised by
          // a previous tool/phase boundary) are NOT reused — each ReAct
          // iteration gets its own collapsible thinking block.
          setMessages((prev) => {
            const { messages: appended, matched } = updateLastBlock(
              prev,
              (b) => b.type === "thinking" && b.isActive && b.node === ev.node,
              (b) => b.type === "thinking"
                ? { ...b, content: b.content + delta }
                : b,
            );
            if (matched) return appended;
            return appendBlock(prev, {
              id: newId("think"),
              type: "thinking",
              node: ev.node,
              content: delta,
              isActive: true,
              startedAt: typeof performance !== "undefined" ? performance.now() : Date.now(),
            });
          });
          return;
        }

        if (ev.event === "tool_call_start") {
          const name = (ev.data.name as string | undefined) ?? "";
          if (!name) return;
          const args = (ev.data.args as Record<string, unknown>) ?? {};
          setMessages((prev) => {
            // A tool call ends the current reasoning burst — collapse first,
            // then append the tool card.
            const collapsed = finalizeActiveThinking(prev, ev.node);
            return appendBlock(collapsed, {
              id: newId("toolcall"),
              type: "tool_call",
              node: ev.node,
              toolName: name,
              args,
              status: "running",
              startedAt: typeof performance !== "undefined" ? performance.now() : Date.now(),
            });
          });
          return;
        }

        if (ev.event === "tool_call_end") {
          const name = (ev.data.name as string | undefined) ?? "";
          const isError = Boolean(ev.data.is_error);
          // Match the most-recent running ToolCallBlock with the same node + toolName.
          setMessages((prev) => {
            let matchedOnce = false;
            const reversed = [...prev].reverse();
            const updated = reversed.map((msg) => {
              const blocksRev = [...msg.blocks].reverse().map((b) => {
                if (matchedOnce) return b;
                if (b.type === "tool_call"
                    && b.status === "running"
                    && b.node === ev.node
                    && b.toolName === name) {
                  matchedOnce = true;
                  const now = typeof performance !== "undefined" ? performance.now() : Date.now();
                  return {
                    ...b,
                    status: isError ? ("error" as const) : ("ok" as const),
                    durationMs: Math.max(0, now - b.startedAt),
                    output: safeStringifyPreview(ev.data.details),
                  };
                }
                return b;
              }).reverse();
              return { ...msg, blocks: blocksRev };
            }).reverse();
            return updated;
          });
          return;
        }

        // Other node_event kinds (iteration, start, done, no_tool_call, max_iters, error)
        // are bookkeeping — surface in a later iteration; spec §6 deferred them.
        return;
      }

      case "error": {
        setIsProcessing(false);
        setMessages((prev) => appendBlock(prev, {
          id: newId("err"),
          type: "error",
          content: ev.content,
        }));
        return;
      }
    }
  }, [currentPhase]);

  useEffect(() => {
    handleEventRef.current = handleEvent;
  }, [handleEvent]);

  // ── connect with exponential backoff + ?thread_id resume ────────────────
  const connect = useCallback(() => {
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING
    ) return;

    intentionalClose.current = false;

    let tid: string | null = null;
    if (typeof window !== "undefined") {
      tid = sessionStorage.getItem(THREAD_ID_KEY);
    }
    const qs = tid ? `?thread_id=${encodeURIComponent(tid)}` : "";
    const pipelineVersion = process.env.NEXT_PUBLIC_PIPELINE_VERSION || "v7";
    const ws = new WebSocket(`${wsBaseUrl}/ws/${pipelineVersion}/chat${qs}`);

    ws.onopen = () => {
      setIsConnected(true);
      reconnectAttempt.current = 0;
    };

    ws.onclose = () => {
      if (wsRef.current === ws) {
        wsRef.current = null;
        setIsConnected(false);
      }
      if (!intentionalClose.current) {
        const delay = Math.min(500 * Math.pow(2, reconnectAttempt.current), 15000);
        reconnectAttempt.current += 1;
        reconnectTimer.current = setTimeout(() => connect(), delay);
      }
    };

    ws.onerror = () => {
      // onclose follows; backoff handled there.
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as ServerEvent;
        handleEventRef.current(data);
      } catch (err) {
        // swallow malformed messages — they're a server bug, not our concern.
        console.error("V7 WS: malformed message", err, e.data);
      }
    };

    wsRef.current = ws;
  }, [wsBaseUrl]);

  useEffect(() => {
    connect();
    return () => {
      intentionalClose.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  // ── send helpers ─────────────────────────────────────────────────────────
  const send = useCallback((msg: ClientMessage) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.warn("V7 WS: send while not connected", msg.type);
      return;
    }
    ws.send(JSON.stringify(msg));
  }, []);

  const sendUserRequest = useCallback((
    text: string,
    opts?: { projectDir?: string; maxRetries?: number; targetOs?: string; targetArch?: string; language?: string },
  ) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setMessages((prev) => [
      ...prev,
      { id: newId("msg"), role: "user", text: trimmed, blocks: [] },
    ]);
    setIsProcessing(true);
    setCurrentPhase("planning");
    setCompletedPhases([]);
    send({
      type: "user_request",
      user_request: trimmed,
      project_dir: opts?.projectDir,
      max_retries: opts?.maxRetries,
      target_os: opts?.targetOs,
      target_arch: opts?.targetArch,
      language: opts?.language,
    });
  }, [send]);

  const sendPlanDecision = useCallback((
    blockId: string,
    approved: boolean,
    opts?: { modifiedPlanMd?: string; reason?: string },
  ) => {
    setIsProcessing(true);
    setMessages((prev) => updateBlock(
      prev,
      (b) => b.id === blockId && b.type === "plan_review",
      (b) => ({ ...(b as any), status: approved ? "approved" : "rejected" }),
    ));
    send({
      type: "plan_decision",
      approved,
      modified_plan_md: opts?.modifiedPlanMd,
      reason: opts?.reason,
    });
  }, [send]);

  const sendEscalationDecision = useCallback((blockId: string, cont: boolean) => {
    setIsProcessing(true);
    setMessages((prev) => updateBlock(
      prev,
      (b) => b.id === blockId && b.type === "escalation",
      (b) => ({ ...(b as any), status: cont ? "continue" : "abort" }),
    ));
    send({ type: "escalation_decision", continue: cont });
    if (!cont && typeof window !== "undefined") {
      sessionStorage.removeItem(THREAD_ID_KEY);
      setThreadId(null);
    }
  }, [send]);

  const sendAbort = useCallback(() => {
    send({ type: "abort" });
    setIsProcessing(false);
  }, [send]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentPhase(null);
    setCompletedPhases([]);
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(THREAD_ID_KEY);
    }
    // Close and reopen so backend rolls a fresh thread_id.
    intentionalClose.current = true;
    wsRef.current?.close();
    setThreadId(null);
    setTimeout(() => {
      intentionalClose.current = false;
      connect();
    }, 50);
  }, [connect]);

  return {
    messages,
    isConnected,
    isProcessing,
    currentPhase,
    completedPhases,
    threadId,
    sendUserRequest,
    sendPlanDecision,
    sendEscalationDecision,
    sendAbort,
    clearMessages,
  };
}
