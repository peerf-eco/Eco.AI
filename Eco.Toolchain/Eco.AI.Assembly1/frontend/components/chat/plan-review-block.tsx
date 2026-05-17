"use client";

import { useState } from "react";
import { CheckCircle2, XCircle, Package, FileText } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { EnhancedMarkdown } from "./enhanced-markdown";
import type { PlanReviewBlock as PlanReviewBlockType } from "./types";

interface PlanReviewBlockProps {
  block: PlanReviewBlockType;
  disabled: boolean;
  onDecision: (approved: boolean, opts?: { modifiedPlanMd?: string; reason?: string }) => void;
}

export function PlanReviewBlock({ block, disabled, onDecision }: PlanReviewBlockProps) {
  const [showEdit, setShowEdit] = useState(false);
  const [edited, setEdited] = useState(block.planMd);
  const [reason, setReason] = useState("");
  const frozen = block.status !== null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-xl overflow-hidden border",
        block.status === "approved" && "border-emerald-500/30",
        block.status === "rejected" && "border-red-500/30",
        !frozen && "border-violet-500/30 shadow-[0_0_24px_rgba(139,92,246,0.08)]",
      )}
    >
      {/* Header */}
      <div className={cn(
        "flex items-center gap-2 px-4 py-2.5 text-sm font-medium",
        block.status === "approved" && "bg-emerald-500/10 text-emerald-300",
        block.status === "rejected" && "bg-red-500/10 text-red-300",
        !frozen && "bg-violet-500/10 text-violet-300",
      )}>
        <Package className="h-4 w-4" />
        <span>Plan review</span>
        {block.projectName && (
          <span className="text-xs text-muted-foreground/70 ml-1">· {block.projectName}</span>
        )}
        {block.status === "approved" && <span className="ml-auto text-xs">Approved</span>}
        {block.status === "rejected" && <span className="ml-auto text-xs">Rejected</span>}
      </div>

      <div className="p-4 space-y-3">
        {/* Plan markdown — toggle between viewer and editable textarea */}
        {!showEdit ? (
          <EnhancedMarkdown
            className="prose prose-sm prose-invert max-w-none leading-relaxed
              prose-p:my-1.5 prose-ul:my-1 prose-li:my-0.5
              prose-code:text-blue-300 prose-code:bg-white/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded"
          >{edited}</EnhancedMarkdown>
        ) : (
          <textarea
            value={edited}
            onChange={(e) => setEdited(e.target.value)}
            rows={12}
            disabled={disabled || frozen}
            className="w-full rounded-lg bg-black/30 border border-white/[0.06] p-3 font-mono text-xs leading-relaxed text-foreground/90 focus:outline-none focus:border-blue-500/40 disabled:opacity-50"
          />
        )}

        {/* Components list */}
        {block.components.length > 0 && (
          <div className="space-y-1.5 pt-2 border-t border-white/[0.04]">
            <div className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">
              Components ({block.components.length})
            </div>
            {block.components.map((c) => (
              <div key={`${c.cid}-${c.version}`} className="flex items-center gap-2 rounded-lg glass px-3 py-1.5 text-xs">
                <span className="font-medium text-foreground">{c.name}</span>
                <span className="text-muted-foreground/60 font-mono text-[10px]">v{c.version}</span>
                <span className="ml-auto text-muted-foreground/70 truncate max-w-[55%]">{c.reason}</span>
              </div>
            ))}
          </div>
        )}

        {/* Reject reason — textarea visible only on rejection workflow */}
        {!frozen && (
          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground transition-colors">
              Add a reason for rejection (optional)
            </summary>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              placeholder="Why should this plan be reworked?"
              className="mt-2 w-full rounded-lg bg-black/30 border border-white/[0.06] p-2 text-xs focus:outline-none focus:border-red-500/40"
            />
          </details>
        )}

        {/* Actions */}
        {!frozen && (
          <div className="flex gap-2 pt-1">
            <Button
              type="button"
              size="sm"
              disabled={disabled}
              onClick={() => onDecision(true, edited !== block.planMd ? { modifiedPlanMd: edited } : undefined)}
              className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-500/15"
            >
              <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />
              Approve
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={disabled}
              onClick={() => onDecision(false, reason ? { reason } : undefined)}
              className="flex-1 hover:bg-red-500/10 hover:text-red-400 border border-white/[0.06]"
            >
              <XCircle className="h-3.5 w-3.5 mr-1.5" />
              Reject
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={disabled}
              onClick={() => setShowEdit((v) => !v)}
              className="hover:bg-white/[0.06]"
              title={showEdit ? "View rendered" : "Edit Markdown"}
            >
              <FileText className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      </div>
    </motion.div>
  );
}
