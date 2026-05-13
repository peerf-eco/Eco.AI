"use client";

import { useState } from "react";
import { ChevronRight, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { ToolCallBlock as ToolCallBlockType } from "./types";

interface ToolCallBlockProps {
  block: ToolCallBlockType;
}

export function ToolCallBlock({ block }: ToolCallBlockProps) {
  const [open, setOpen] = useState(false);

  const StatusIcon = block.status === "running"
    ? Loader2
    : block.status === "ok"
      ? CheckCircle2
      : XCircle;

  const statusTone =
    block.status === "running" ? "text-blue-300" :
    block.status === "ok"      ? "text-emerald-300" :
                                 "text-red-300";

  const borderTone =
    block.status === "running" ? "border-blue-500/25" :
    block.status === "ok"      ? "border-emerald-500/20" :
                                 "border-red-500/25";

  const argsPreview = (() => {
    try {
      const s = JSON.stringify(block.args);
      return s.length > 80 ? s.slice(0, 80) + "…" : s;
    } catch {
      return "<unserializable args>";
    }
  })();

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("rounded-lg border bg-white/[0.02] overflow-hidden", borderTone)}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-white/[0.03] transition-colors"
      >
        <ChevronRight className={cn("h-3 w-3 transition-transform", open && "rotate-90")} />
        <StatusIcon className={cn("h-3.5 w-3.5", statusTone, block.status === "running" && "animate-spin")} />
        <span className="font-mono text-foreground/85">{block.toolName}</span>
        <span className="text-muted-foreground/60 truncate flex-1 text-left">{argsPreview}</span>
        {block.durationMs !== undefined && (
          <span className="text-[10px] text-muted-foreground/60 font-mono">
            {Math.round(block.durationMs)}ms
          </span>
        )}
      </button>
      {open && (
        <div className="px-3 pb-3 pt-1 text-[11px] space-y-2">
          <div>
            <span className="text-muted-foreground/60 uppercase tracking-wide">Args</span>
            <pre className="mt-1 px-2 py-1.5 rounded bg-black/40 font-mono leading-relaxed whitespace-pre-wrap max-h-40 overflow-auto text-foreground/85">
{JSON.stringify(block.args, null, 2)}
            </pre>
          </div>
          {block.output && (
            <div>
              <span className="text-muted-foreground/60 uppercase tracking-wide">Output</span>
              <pre className="mt-1 px-2 py-1.5 rounded bg-black/40 font-mono leading-relaxed whitespace-pre-wrap max-h-40 overflow-auto text-foreground/85">
{block.output}
              </pre>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
