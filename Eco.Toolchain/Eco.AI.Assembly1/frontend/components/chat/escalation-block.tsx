"use client";

import { AlertTriangle, Play, X } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { EscalationBlock as EscalationBlockType } from "./types";

interface EscalationBlockProps {
  block: EscalationBlockType;
  disabled: boolean;
  onDecision: (cont: boolean) => void;
}

const REASON_LABEL: Record<string, string> = {
  planner_max_iters:    "Planner timed out",
  planner_no_tool_call: "Planner gave no answer",
  planner_error:        "Planner crashed",
  setup_max_iters:      "Setup timed out",
  setup_no_tool_call:   "Setup gave no answer",
  setup_error:          "Setup crashed",
  coder_max_iters:      "Coder timed out",
  coder_no_tool_call:   "Coder gave no answer",
  coder_error:          "Coder crashed",
  builder_retry_limit:  "Builder hit retry ceiling",
  builder_max_iters:    "Builder timed out",
  builder_no_tool_call: "Builder gave no answer",
  builder_error:        "Builder crashed",
  tester_retry_limit:   "Tester hit retry ceiling",
  tester_max_iters:     "Tester timed out",
  tester_no_tool_call:  "Tester gave no answer",
  tester_error:         "Tester crashed",
};

function headerText(reason: string, retryCount: number, maxRetries: number): { primary: string; secondary: string } {
  const primary = REASON_LABEL[reason] || `Pipeline escalated: ${reason || "unknown"}`;
  const isRetryLimit = reason.endsWith("_retry_limit");
  const secondary = isRetryLimit && retryCount > 0
    ? `${retryCount}/${maxRetries || retryCount} retries used`
    : "First attempt";
  return { primary, secondary };
}

export function EscalationBlock({ block, disabled, onDecision }: EscalationBlockProps) {
  const frozen = block.status !== null;
  const { primary, secondary } = headerText(block.reason, block.retryCount, block.maxRetries);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-xl overflow-hidden border",
        block.status === "continue" && "border-blue-500/30",
        block.status === "abort"    && "border-red-500/30",
        !frozen && "border-yellow-500/30 shadow-[0_0_24px_rgba(234,179,8,0.08)]",
      )}
    >
      <div className={cn(
        "flex items-center gap-2 px-4 py-2.5 text-sm font-medium",
        block.status === "continue" && "bg-blue-500/10 text-blue-300",
        block.status === "abort"    && "bg-red-500/10 text-red-300",
        !frozen && "bg-yellow-500/10 text-yellow-300",
      )}>
        <AlertTriangle className="h-4 w-4" />
        <span>{primary}</span>
        <span className="ml-auto text-xs text-muted-foreground/80">{secondary}</span>
      </div>

      <div className="p-4 space-y-3">
        <p className="text-xs text-muted-foreground leading-relaxed">
          The pipeline paused. Review the diagnostics below and decide whether
          to retry from the coder or stop the run.
        </p>

        {block.buildLog && (
          <details className="rounded-lg bg-black/30 border border-white/[0.04]" open>
            <summary className="cursor-pointer px-3 py-2 text-[11px] uppercase tracking-wide font-medium text-red-300/80">
              Build log
            </summary>
            <pre className="px-3 pb-3 font-mono text-[11px] leading-relaxed text-foreground/85 whitespace-pre-wrap max-h-60 overflow-auto">
{block.buildLog}
            </pre>
          </details>
        )}

        {block.testerReportMd && (
          <details className="rounded-lg bg-black/30 border border-white/[0.04]">
            <summary className="cursor-pointer px-3 py-2 text-[11px] uppercase tracking-wide font-medium text-orange-300/80">
              Tester report
            </summary>
            <pre className="px-3 pb-3 font-mono text-[11px] leading-relaxed text-foreground/85 whitespace-pre-wrap max-h-60 overflow-auto">
{block.testerReportMd}
            </pre>
          </details>
        )}

        {block.coderSummaryMd && (
          <details className="rounded-lg bg-black/30 border border-white/[0.04]">
            <summary className="cursor-pointer px-3 py-2 text-[11px] uppercase tracking-wide font-medium text-muted-foreground">
              Last coder summary
            </summary>
            <pre className="px-3 pb-3 font-mono text-[11px] leading-relaxed text-foreground/70 whitespace-pre-wrap max-h-40 overflow-auto">
{block.coderSummaryMd}
            </pre>
          </details>
        )}

        {!frozen && (
          <div className="flex gap-2 pt-1">
            <Button
              type="button"
              size="sm"
              disabled={disabled}
              onClick={() => onDecision(true)}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/15"
            >
              <Play className="h-3.5 w-3.5 mr-1.5" />
              Continue
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={disabled}
              onClick={() => onDecision(false)}
              className="flex-1 hover:bg-red-500/10 hover:text-red-400 border border-white/[0.06]"
            >
              <X className="h-3.5 w-3.5 mr-1.5" />
              Abort
            </Button>
          </div>
        )}
        {block.status === "continue" && (
          <div className="text-xs text-blue-300">Continuing — retry counter reset.</div>
        )}
        {block.status === "abort" && (
          <div className="text-xs text-red-300">Pipeline aborted.</div>
        )}
      </div>
    </motion.div>
  );
}
