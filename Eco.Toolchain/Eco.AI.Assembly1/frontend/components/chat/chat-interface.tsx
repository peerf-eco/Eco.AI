"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send, Bot, User, Cpu, Settings, X, Sparkles, StopCircle, RotateCcw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { RagInitializer } from "./rag-initializer";
import { PhaseStepper } from "./phase-stepper";
import { StreamMessage } from "./stream-message";
import { useV6Socket } from "./use-v6-socket";
import type { ChatMessage } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = API_URL.replace(/^http/, "ws");

const EXAMPLES = [
  "Собери калькулятор с pow и sqrt",
  "Создай приложение, выводящее sin/cos для углов от 0 до 90",
  "Сделай конвертер температур из Цельсия в Фаренгейт",
];

export function ChatInterface() {
  const [input, setInput] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  const {
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
  } = useV6Socket(WS_BASE);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const onSend = () => {
    if (!input.trim() || !isConnected || isProcessing) return;
    sendUserRequest(input);
    setInput("");
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Ambient glow */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/[0.03] rounded-full blur-[128px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-violet-500/[0.03] rounded-full blur-[128px]" />
      </div>

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
              className="fixed inset-y-0 right-0 z-50 w-80 glass-strong p-5 shadow-2xl"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-gradient">Settings</h2>
                <Button variant="ghost" size="icon" onClick={() => setShowSettings(false)} className="hover:bg-white/10">
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <RagInitializer />
              {threadId && (
                <div className="mt-6 pt-4 border-t border-white/[0.06] text-xs text-muted-foreground">
                  <div className="uppercase tracking-wide text-[10px] mb-1">Thread</div>
                  <div className="font-mono text-foreground/80 break-all">{threadId}</div>
                </div>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main */}
      <div className="flex flex-1 flex-col relative z-10">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 glass border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-violet-500 shadow-lg shadow-blue-500/20">
              <Cpu className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold tracking-tight">EcoOS Component Agent</h1>
              <p className="text-xs text-muted-foreground">V6 Five-Node Pipeline</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
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

            <div ref={scrollAnchorRef} />
          </div>
        </ScrollArea>

        {/* Input dock */}
        <div className="px-4 pb-4 pt-2">
          <div className="mx-auto max-w-3xl">
            <div className="flex gap-2 rounded-xl glass p-2 transition-all focus-within:glow-blue focus-within:border-blue-500/30">
              <Input
                placeholder="Опишите приложение для сборки из SDK-компонентов EcoOS…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), onSend())}
                disabled={!isConnected || isProcessing}
                className="border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-sm placeholder:text-muted-foreground/60"
              />
              {isProcessing ? (
                <Button
                  onClick={sendAbort}
                  size="icon"
                  variant="ghost"
                  className="shrink-0 rounded-lg hover:bg-red-500/10 hover:text-red-400"
                  title="Stop"
                >
                  <StopCircle size={18} />
                </Button>
              ) : (
                <Button
                  onClick={onSend}
                  disabled={!isConnected || !input.trim()}
                  size="icon"
                  className="shrink-0 rounded-lg bg-gradient-to-r from-blue-500 to-violet-500 hover:from-blue-600 hover:to-violet-600 shadow-lg shadow-blue-500/20 disabled:opacity-30 disabled:shadow-none transition-all"
                >
                  <Send size={16} />
                </Button>
              )}
            </div>
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
