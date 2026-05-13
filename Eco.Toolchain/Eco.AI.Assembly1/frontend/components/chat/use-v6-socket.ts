"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  Block,
  ChatMessage,
  ClientMessage,
  PipelineNode,
  ServerEvent,
  V6Phase,
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

const THREAD_ID_KEY = "ecov6.thread_id";

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

// ────────────────────────────────────────────────────────────────────────────
// useV6Socket — single source of truth for the V6 chat UI.
// ────────────────────────────────────────────────────────────────────────────

export interface UseV6SocketResult {
  messages: ChatMessage[];
  isConnected: boolean;
  isProcessing: boolean;
  currentPhase: V6Phase | null;
  completedPhases: V6Phase[];
  threadId: string | null;

  sendUserRequest: (text: string, opts?: { projectDir?: string; maxRetries?: number }) => void;
  sendPlanDecision: (blockId: string, approved: boolean, opts?: { modifiedPlanMd?: string; reason?: string }) => void;
  sendEscalationDecision: (blockId: string, cont: boolean) => void;
  sendAbort: () => void;
  clearMessages: () => void;
}

export function useV6Socket(wsBaseUrl: string): UseV6SocketResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<V6Phase | null>(null);
  const [completedPhases, setCompletedPhases] = useState<V6Phase[]>([]);
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
        setMessages((prev) => appendBlock(prev, {
          id: newId("phase"),
          type: "phase_header",
          phase: ev.phase,
          node: ev.node,
        }));
        return;
      }

      case "node_done": {
        setMessages((prev) => appendBlock(prev, {
          id: newId("nodedone"),
          type: "node_done",
          node: ev.node as PipelineNode,
          projectName: ev.project_name,
          componentsCount: ev.components_count,
          downloadedPaths: ev.downloaded_paths,
          summaryMd: ev.summary_md,
          buildArtifact: ev.build_artifact,
          reasonMd: ev.reason_md,
        }));
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

      case "max_retry_escalation": {
        setIsProcessing(false);
        setMessages((prev) => appendBlock(prev, {
          id: newId("escalation"),
          type: "escalation",
          failureOrigin: ev.failure_origin || "",
          retryCount: ev.retry_count || 0,
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
        setMessages((prev) => appendBlock(prev, {
          id: newId("done"),
          type: "pipeline_done",
          status: ev.status,
          buildArtifact: ev.build_artifact || "",
          testerReportMd: ev.tester_report_md || "",
        }));
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
    const ws = new WebSocket(`${wsBaseUrl}/ws/v6/chat${qs}`);

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
        console.error("V6 WS: malformed message", err, e.data);
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
      console.warn("V6 WS: send while not connected", msg.type);
      return;
    }
    ws.send(JSON.stringify(msg));
  }, []);

  const sendUserRequest = useCallback((
    text: string,
    opts?: { projectDir?: string; maxRetries?: number },
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
