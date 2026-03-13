"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send, Bot, User, FileCode, Settings, X,
  CheckCircle2, XCircle, FlaskConical, Cpu, Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { ProgressViewer, Stage } from "./progress-viewer";
import { RagInitializer } from "./rag-initializer";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = API_URL.replace(/^http/, "ws");

interface Message {
  role: "user" | "assistant";
  content: string;
  files?: GeneratedFile[];
  result?: ResultData;
}

interface GeneratedFile {
  path: string;
  type: string;
  url: string;
}

interface ResultData {
  is_success: boolean;
  tests_passed?: boolean;
  project_dir: string;
  build_result: string;
  test_results?: string;
  iterations: number;
  resolved_components: { name: string; cid: string }[];
  missing_components: string[];
}

const msgVariants = {
  hidden: { opacity: 0, y: 12, scale: 0.97 },
  visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.3, ease: "easeOut" } },
};

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [currentStage, setCurrentStage] = useState<Stage>("planner");
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [showSettings, setShowSettings] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const threadId = useRef(Math.random().toString(36).substring(7));
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalClose = useRef(false);
  const handleWsMessageRef = useRef<(data: any) => void>(() => {});

  const connect = useCallback(() => {
    // Guard: don't open if already open or connecting
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING
    ) return;

    intentionalClose.current = false; // Reset on every connect attempt

    const ws = new WebSocket(`${WS_URL}/ws/chat/${threadId.current}`);

    ws.onopen = () => {
      console.log("Connected to agent");
      setIsConnected(true);
      reconnectAttempt.current = 0;
    };

    ws.onclose = (e) => {
      console.log(`Disconnected (code=${e.code})`);
      // Only update state if THIS ws is still the current one (avoids StrictMode race)
      if (wsRef.current === ws) {
        wsRef.current = null;
        setIsConnected(false);
      }

      if (!intentionalClose.current) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempt.current), 30000);
        reconnectAttempt.current++;
        console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempt.current})`);
        reconnectTimer.current = setTimeout(() => connect(), delay);
      }
    };

    ws.onerror = (e) => {
      console.error("WebSocket error:", e);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "heartbeat") return;
      handleWsMessageRef.current(data);
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();

    return () => {
      intentionalClose.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, statusMessage]);

  const handleWsMessage = useCallback((data: any) => {
    switch (data.type) {
      case "token":
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.role === "assistant") {
            return [
              ...prev.slice(0, -1),
              { ...lastMsg, content: lastMsg.content + data.content },
            ];
          } else {
            return [...prev, { role: "assistant", content: data.content }];
          }
        });
        break;

      case "progress":
        if (data.status === "running") {
          setCurrentStage(data.stage);
          setIsProcessing(true);
        }
        break;

      case "status":
        setStatusMessage(data.content);
        break;

      case "files":
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.role === "assistant") {
            return [
              ...prev.slice(0, -1),
              { ...lastMsg, files: data.files },
            ];
          }
          return prev;
        });
        break;

      case "result":
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.role === "assistant") {
            return [
              ...prev.slice(0, -1),
              { ...lastMsg, result: data.data },
            ];
          }
          return [...prev, { role: "assistant", content: "", result: data.data }];
        });
        break;

      case "done":
        setIsProcessing(false);
        setCurrentStage("complete");
        setStatusMessage("");
        break;

      case "error":
        console.error("Agent error:", data.content);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${data.content}` },
        ]);
        setIsProcessing(false);
        break;
    }
  }, []);

  // Keep ref in sync so WebSocket onmessage always calls the latest handler
  useEffect(() => {
    handleWsMessageRef.current = handleWsMessage;
  }, [handleWsMessage]);

  const sendMessage = () => {
    if (!input.trim() || !isConnected) return;

    setMessages((prev) => [...prev, { role: "user", content: input }]);
    wsRef.current?.send(JSON.stringify({ message: input }));
    setInput("");
    setIsProcessing(true);
    setCurrentStage("planner");
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Ambient background glow */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/[0.03] rounded-full blur-[128px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-violet-500/[0.03] rounded-full blur-[128px]" />
      </div>

      {/* Settings Sidebar */}
      <AnimatePresence>
        {showSettings && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
              onClick={() => setShowSettings(false)}
            />
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="fixed inset-y-0 right-0 z-50 w-80 glass-strong p-5 shadow-2xl"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-gradient">Settings</h2>
                <Button variant="ghost" size="icon" onClick={() => setShowSettings(false)} className="hover:bg-white/10">
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <RagInitializer />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex flex-1 flex-col relative z-10">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 glass border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-violet-500 shadow-lg shadow-blue-500/20">
              <Cpu className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold tracking-tight">EcoOS Component Agent</h1>
              <p className="text-xs text-muted-foreground">
                V3 Assembly Pipeline
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-full glass px-3 py-1.5">
              <div className={cn(
                "h-2 w-2 rounded-full transition-colors",
                isConnected ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" : "bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.5)]"
              )} />
              <span className="text-xs text-muted-foreground">{isConnected ? "Connected" : "Offline"}</span>
            </div>
            <Button variant="ghost" size="icon" onClick={() => setShowSettings(true)} className="hover:bg-white/10 rounded-lg">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </header>

        {/* Chat Area */}
        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-3xl px-4 py-6 space-y-5">
            {/* Empty state */}
            {messages.length === 0 && !isProcessing && (
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
                  Describe the EcoOS application you want to create. The agent will search SDK components,
                  resolve dependencies, generate code, build, and run tests.
                </p>
                <div className="flex gap-2 mt-6">
                  {["Calculator app", "Linked list", "Matrix operations"].map((ex) => (
                    <button
                      key={ex}
                      onClick={() => setInput(ex)}
                      className="rounded-lg glass px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-white/[0.06] transition-colors"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Messages */}
            <AnimatePresence initial={false}>
              {messages.map((msg, idx) => (
                <motion.div
                  key={idx}
                  variants={msgVariants}
                  initial="hidden"
                  animate="visible"
                  layout
                  className={cn(
                    "flex gap-3",
                    msg.role === "user" ? "flex-row-reverse" : "flex-row"
                  )}
                >
                  <div
                    className={cn(
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                      msg.role === "user"
                        ? "bg-gradient-to-br from-blue-500 to-violet-500 text-white shadow-lg shadow-blue-500/20"
                        : "glass"
                    )}
                  >
                    {msg.role === "user" ? <User size={14} /> : <Bot size={14} />}
                  </div>

                  <div className="flex max-w-[80%] flex-col gap-2">
                    {msg.content && (
                      <div className={cn(
                        "rounded-xl px-4 py-3",
                        msg.role === "user"
                          ? "bg-gradient-to-r from-blue-600/80 to-violet-600/80 text-white shadow-lg shadow-blue-500/10"
                          : "glass"
                      )}>
                        <div className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</div>
                      </div>
                    )}

                    {msg.result && <ResultCard result={msg.result} />}

                    {msg.files && (
                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        {msg.files.map((file, fIdx) => (
                          <a
                            key={fIdx}
                            href={`${API_URL}${file.url}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 rounded-lg glass px-3 py-2 text-sm hover:bg-white/[0.06] transition-colors group"
                          >
                            <FileCode className="h-4 w-4 text-blue-400 group-hover:text-blue-300 transition-colors" />
                            <span className="truncate">{file.path}</span>
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Processing indicator */}
            <AnimatePresence>
              {isProcessing && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  className="rounded-xl glass p-4 glow-blue"
                >
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
                    <Bot size={16} className="text-blue-400" />
                    <span>{statusMessage || "Processing..."}</span>
                  </div>
                  <ProgressViewer currentStage={currentStage} isProcessing={isProcessing} />
                </motion.div>
              )}
            </AnimatePresence>

            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="px-4 pb-4 pt-2">
          <div className="mx-auto max-w-3xl">
            <div className="flex gap-2 rounded-xl glass p-2 transition-all focus-within:glow-blue focus-within:border-blue-500/30">
              <Input
                placeholder="Describe the EcoOS application you want to create..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                disabled={!isConnected || isProcessing}
                className="border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-sm placeholder:text-muted-foreground/60"
              />
              <Button
                onClick={sendMessage}
                disabled={!isConnected || isProcessing || !input.trim()}
                size="icon"
                className="shrink-0 rounded-lg bg-gradient-to-r from-blue-500 to-violet-500 hover:from-blue-600 hover:to-violet-600 shadow-lg shadow-blue-500/20 disabled:opacity-30 disabled:shadow-none transition-all"
              >
                <Send size={16} />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ResultCard({ result }: { result: ResultData }) {
  const buildOk = result.is_success;
  const testsOk = result.tests_passed ?? false;
  const hasTests = result.test_results && result.test_results.length > 0;

  const allGood = buildOk && testsOk;
  const buildOnly = buildOk && !testsOk;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "rounded-xl overflow-hidden border",
        allGood ? "border-emerald-500/20 glow-green" : buildOnly ? "border-yellow-500/20" : "border-red-500/20 glow-red"
      )}
    >
      {/* Status header */}
      <div className={cn(
        "flex items-center gap-2 px-4 py-2.5 text-sm font-medium",
        allGood
          ? "bg-emerald-500/10 text-emerald-400"
          : buildOnly
          ? "bg-yellow-500/10 text-yellow-400"
          : "bg-red-500/10 text-red-400"
      )}>
        {allGood ? (
          <CheckCircle2 className="h-4 w-4" />
        ) : (
          <XCircle className="h-4 w-4" />
        )}
        {allGood
          ? "Build & Tests Passed"
          : buildOnly
          ? "Build OK, Tests Failed"
          : "Build Failed"}
        <span className="ml-auto text-xs opacity-60">{result.iterations} iter.</span>
      </div>

      <div className="space-y-3 p-4 text-sm">
        {/* Components */}
        {result.resolved_components.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {result.resolved_components.map((c) => (
              <span key={c.cid} className="rounded-md glass px-2 py-0.5 text-xs text-muted-foreground">
                {c.name}
              </span>
            ))}
          </div>
        )}

        {/* Missing components */}
        {result.missing_components.length > 0 && (
          <div className="rounded-lg bg-red-500/10 px-3 py-2 text-red-400 text-xs">
            Missing: {result.missing_components.join(", ")}
          </div>
        )}

        {/* Test results */}
        {hasTests && (
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5 font-medium text-xs text-muted-foreground uppercase tracking-wide">
              <FlaskConical className="h-3.5 w-3.5" />
              Test Results
            </div>
            <div className="rounded-lg bg-black/30 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap border border-white/[0.04]">
              {result.test_results}
            </div>
          </div>
        )}

        {/* Build output on failure */}
        {!buildOk && result.build_result && (
          <div className="space-y-1.5">
            <div className="font-medium text-xs text-muted-foreground uppercase tracking-wide">Build Output</div>
            <div className="max-h-40 overflow-auto rounded-lg bg-black/30 p-3 font-mono text-xs whitespace-pre-wrap border border-white/[0.04]">
              {result.build_result.slice(0, 2000)}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
