"use client";

import {
  Bot,
  CheckCircle2,
  XCircle,
  Hammer,
  FlaskConical,
  Package,
  Code2,
  Download,
  AlertCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { PlanReviewBlock as PlanReviewBlockView } from "./plan-review-block";
import { EscalationBlock as EscalationBlockView } from "./escalation-block";
import { ToolCallBlock as ToolCallBlockView } from "./tool-call-block";
import {
  PHASE_LABEL,
  type Block,
  type ChatMessage,
  type PipelineNode,
} from "./types";

const NODE_ICON: Record<PipelineNode, React.ComponentType<{ className?: string }>> = {
  planner:    Package,
  plan_gate:  Package,
  setup:      Download,
  coder:      Code2,
  builder:    Hammer,
  tester:     FlaskConical,
  escalate:   AlertCircle,
};

const NODE_LABEL: Record<PipelineNode, string> = {
  planner:    "Planner",
  plan_gate:  "Plan gate",
  setup:      "Setup",
  coder:      "Coder",
  builder:    "Builder",
  tester:     "Tester",
  escalate:   "Escalation",
};

interface StreamMessageProps {
  message: ChatMessage;
  disabled: boolean;
  onPlanDecision: (blockId: string, approved: boolean, opts?: { modifiedPlanMd?: string; reason?: string }) => void;
  onEscalationDecision: (blockId: string, cont: boolean) => void;
}

export function StreamMessage({ message, disabled, onPlanDecision, onEscalationDecision }: StreamMessageProps) {
  // User messages are simple single-line bubbles handled in chat-interface.
  // This component only renders assistant messages.
  return (
    <div className="flex gap-3 flex-row">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg glass">
        <Bot size={14} />
      </div>
      <div className="flex max-w-[80%] flex-col gap-2 flex-1">
        {message.blocks.map((block) => (
          <BlockView
            key={block.id}
            block={block}
            disabled={disabled}
            onPlanDecision={onPlanDecision}
            onEscalationDecision={onEscalationDecision}
          />
        ))}
      </div>
    </div>
  );
}

function BlockView({
  block,
  disabled,
  onPlanDecision,
  onEscalationDecision,
}: {
  block: Block;
  disabled: boolean;
  onPlanDecision: StreamMessageProps["onPlanDecision"];
  onEscalationDecision: StreamMessageProps["onEscalationDecision"];
}) {
  switch (block.type) {
    case "text":
      return (
        <div className="rounded-xl px-4 py-3 glass">
          <div className="prose prose-sm prose-invert max-w-none leading-relaxed
            prose-p:my-1.5 prose-headings:my-2 prose-ul:my-1.5 prose-ol:my-1.5
            prose-li:my-0.5 prose-pre:my-2 prose-strong:text-white
            prose-code:text-blue-300 prose-code:bg-white/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
            <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>{block.content}</ReactMarkdown>
          </div>
        </div>
      );

    case "phase_header": {
      const NodeIcon = block.node ? NODE_ICON[block.node as PipelineNode] : Bot;
      return (
        <motion.div
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-white/[0.02] border-l-2 border-blue-500/40 text-xs"
        >
          <NodeIcon className="h-3.5 w-3.5 text-blue-400" />
          <span className="font-medium text-blue-300">{PHASE_LABEL[block.phase]}</span>
          {block.node && (
            <span className="text-muted-foreground/60 text-[10px] uppercase tracking-wide ml-1">
              · {NODE_LABEL[block.node as PipelineNode] || block.node}
            </span>
          )}
        </motion.div>
      );
    }

    case "node_done": {
      const NodeIcon = NODE_ICON[block.node];
      const details: { label: string; value: string }[] = [];
      if (block.projectName) details.push({ label: "Project", value: block.projectName });
      if (block.componentsCount !== undefined) details.push({ label: "Components", value: String(block.componentsCount) });
      if (block.downloadedPaths?.length) details.push({ label: "Pulled", value: `${block.downloadedPaths.length} pkg` });
      if (block.buildArtifact) details.push({ label: "Artifact", value: block.buildArtifact.split(/[\\/]/).pop() || block.buildArtifact });

      return (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-lg glass border border-emerald-500/20 px-3 py-2"
        >
          <div className="flex items-center gap-2 text-xs">
            <NodeIcon className="h-3.5 w-3.5 text-emerald-400" />
            <span className="font-medium text-emerald-300">{NODE_LABEL[block.node]}</span>
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 ml-auto" />
          </div>
          {details.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
              {details.map((d) => (
                <span key={d.label}>
                  <span className="text-muted-foreground/60">{d.label}:</span>{" "}
                  <span className="text-foreground/80 font-mono">{d.value}</span>
                </span>
              ))}
            </div>
          )}
          {block.summaryMd && (
            <details className="mt-2 text-xs">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground transition-colors">
                Summary
              </summary>
              <div className="mt-1 prose prose-sm prose-invert max-w-none prose-p:my-1">
                <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>{block.summaryMd}</ReactMarkdown>
              </div>
            </details>
          )}
          {block.reasonMd && (
            <div className="mt-2 text-xs text-muted-foreground italic">
              {block.reasonMd}
            </div>
          )}
        </motion.div>
      );
    }

    case "build_fail":
    case "test_fail": {
      const isBuild = block.type === "build_fail";
      const Icon = isBuild ? Hammer : FlaskConical;
      const label = isBuild ? "Build failed" : "Test failed";
      return (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-lg border border-red-500/25 bg-red-500/[0.04] overflow-hidden"
        >
          <div className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-red-300">
            <Icon className="h-3.5 w-3.5" />
            <span>{label}</span>
            <span className="ml-auto text-muted-foreground/70">retry {block.retryCount}</span>
          </div>
          <pre className="px-3 pb-3 font-mono text-[11px] leading-relaxed text-foreground/85 whitespace-pre-wrap max-h-60 overflow-auto">
{block.message}
          </pre>
        </motion.div>
      );
    }

    case "tool_call":
      return <ToolCallBlockView block={block} />;

    case "plan_review":
      return (
        <PlanReviewBlockView
          block={block}
          disabled={disabled}
          onDecision={(approved, opts) => onPlanDecision(block.id, approved, opts)}
        />
      );

    case "escalation":
      return (
        <EscalationBlockView
          block={block}
          disabled={disabled}
          onDecision={(cont) => onEscalationDecision(block.id, cont)}
        />
      );

    case "pipeline_done": {
      const ok = block.status === "success";
      const Icon = ok ? CheckCircle2 : XCircle;
      const tone = ok ? "emerald" : block.status === "user_aborted" ? "muted" : "red";
      return (
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2 }}
          className={cn(
            "rounded-xl overflow-hidden border",
            tone === "emerald" && "border-emerald-500/30",
            tone === "muted"   && "border-white/[0.06]",
            tone === "red"     && "border-red-500/30",
          )}
        >
          <div className={cn(
            "flex items-center gap-2 px-4 py-2.5 text-sm font-medium",
            tone === "emerald" && "bg-emerald-500/10 text-emerald-300",
            tone === "muted"   && "bg-white/[0.03] text-muted-foreground",
            tone === "red"     && "bg-red-500/10 text-red-300",
          )}>
            <Icon className="h-4 w-4" />
            <span>Pipeline · {block.status}</span>
          </div>
          {(block.buildArtifact || block.testerReportMd) && (
            <div className="p-4 space-y-2 text-xs">
              {block.buildArtifact && (
                <div>
                  <span className="text-muted-foreground/60">Artifact: </span>
                  <span className="font-mono text-foreground/85">{block.buildArtifact}</span>
                </div>
              )}
              {block.testerReportMd && (
                <details>
                  <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                    Tester report
                  </summary>
                  <div className="mt-1 prose prose-sm prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>{block.testerReportMd}</ReactMarkdown>
                  </div>
                </details>
              )}
            </div>
          )}
        </motion.div>
      );
    }

    case "error":
      return (
        <div className="rounded-lg border border-red-500/30 bg-red-500/[0.06] px-3 py-2 text-xs text-red-300">
          <span className="font-medium">Error: </span>
          {block.content}
        </div>
      );
  }
}
