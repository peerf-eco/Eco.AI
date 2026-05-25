"use client";

import { useEffect, useState } from "react";
import { ChevronRight, Brain } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { ThinkingBlock as ThinkingBlockType } from "./types";

interface ThinkingBlockProps {
  block: ThinkingBlockType;
}

// Pattern borrowed from F:\ai-mek\repos\mek-ai-client\src\chat\StreamMessage.tsx:97-129.
// Each ReAct iteration produces its own thinking block; while streaming we
// keep it expanded with a live pulsing dot and a CSS-only blinking caret at
// the end of the text. When the backend emits tool_call_start / phase_change
// / pipeline_done / node_done, use-v6-socket flips `isActive` to false and a
// useEffect here collapses the block. The history is never deleted — the
// user can re-expand any past iteration to reread the reasoning.
export function ThinkingBlock({ block }: ThinkingBlockProps) {
  const [open, setOpen] = useState(block.isActive);

  useEffect(() => {
    if (!block.isActive) setOpen(false);
  }, [block.isActive]);

  // Token estimate, GPT-style ~4 chars/token. Header label only.
  const tokenEstimate = Math.max(1, Math.round(block.content.length / 4));

  const borderTone = block.isActive ? "border-blue-500/30" : "border-white/[0.06]";

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-lg border bg-white/[0.02] overflow-hidden",
        borderTone,
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-white/[0.03] transition-colors"
      >
        <ChevronRight className={cn("h-3 w-3 transition-transform", open && "rotate-90")} />
        <Brain className={cn("h-3.5 w-3.5", block.isActive ? "text-blue-300" : "text-muted-foreground/70")} />
        <span className={cn("font-medium", block.isActive ? "text-blue-200" : "text-foreground/75")}>
          Thinking
        </span>
        <span className="text-muted-foreground/50 text-[10px] uppercase tracking-wide">
          · {block.node}
        </span>
        {block.isActive && (
          <span
            aria-hidden
            className="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-blue-400 thinking-pulse"
          />
        )}
        <span className="ml-auto text-[10px] text-muted-foreground/60 font-mono">
          ~{tokenEstimate} tok
        </span>
      </button>
      {open && (
        <div className="px-3 pb-3 pt-1">
          <pre
            className={cn(
              "font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words text-foreground/80",
              block.isActive && "thinking-caret",
            )}
          >
{block.content}
          </pre>
        </div>
      )}
    </motion.div>
  );
}
