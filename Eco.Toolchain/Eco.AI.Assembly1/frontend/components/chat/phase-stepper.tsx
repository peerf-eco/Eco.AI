"use client";

import { CheckCircle2, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  PHASE_LABEL,
  stepperStepsForMode,
  type HarnessPhase,
  type PhaseTokenMap,
  type StepperStep,
  type TokenStat,
  type WorkingMode,
} from "./types";

interface PhaseStepperProps {
  mode: WorkingMode;
  currentPhase: HarnessPhase | null;
  completedPhases: HarnessPhase[];
  phaseTokens: PhaseTokenMap;
}

type StepState = "pending" | "active" | "completed";

function stepState(step: StepperStep, current: HarnessPhase | null, completed: HarnessPhase[]): StepState {
  if (completed.includes(step.phase)) return "completed";
  if (current === step.phase) return "active";
  // awaiting_approval visually still belongs to Planning.
  if (current === "awaiting_approval" && step.phase === "planning") return "active";
  return "pending";
}

export function PhaseStepper({
  mode,
  currentPhase,
  completedPhases,
  phaseTokens,
}: PhaseStepperProps) {
  const steps = stepperStepsForMode(mode);
  return (
    <div className="relative glass border-b border-white/[0.06] px-6 py-3">
      <div className="flex items-center gap-2">
        {steps.map((step, i) => {
          const state = stepState(step, currentPhase, completedPhases);
          const isLast = i === steps.length - 1;
          return (
            <div key={`${step.phase}-${step.label}`} className="flex items-center gap-2 flex-1 last:flex-initial">
              <StepDot step={step} state={state} index={i} />
              {!isLast && (
                <Connector
                  active={state === "completed"}
                  stepActive={state === "active"}
                  phase={step.phase}
                  tokens={phaseTokens[step.phase]}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface StepDotProps {
  step: StepperStep;
  state: StepState;
  index: number;
}

function StepDot({ step, state, index }: StepDotProps) {
  return (
    <div className="flex items-center gap-2 shrink-0">
      <motion.div
        initial={false}
        animate={{
          scale: state === "active" ? 1.05 : 1,
        }}
        transition={{ duration: 0.2 }}
        className={cn(
          "flex h-7 w-7 items-center justify-center rounded-full border text-[11px] font-medium transition-colors",
          state === "completed" && "bg-emerald-500/15 border-emerald-500/40 text-emerald-400",
          state === "active"    && "bg-blue-500/15 border-blue-500/50 text-blue-400 shadow-[0_0_12px_rgba(59,130,246,0.25)]",
          state === "pending"   && "bg-white/[0.03] border-white/[0.08] text-muted-foreground/60",
        )}
      >
        {state === "completed" ? (
          <CheckCircle2 className="h-4 w-4" />
        ) : state === "active" ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <span>{index + 1}</span>
        )}
      </motion.div>
      <span className={cn(
        "text-xs tracking-tight whitespace-nowrap transition-colors",
        state === "completed" && "text-emerald-300",
        state === "active"    && "text-blue-300",
        state === "pending"   && "text-muted-foreground/50",
      )}>
        {step.label ?? PHASE_LABEL[step.phase]}
      </span>
    </div>
  );
}

function Connector({
  active,
  stepActive,
  phase,
  tokens,
}: {
  active: boolean;
  stepActive: boolean;
  phase: HarnessPhase;
  tokens?: TokenStat;
}) {
  // UI_PRD I-5: the counter oval used to render only after the phase's first
  // completed LLM call — during a long in-flight call it was missing (or
  // stale) with no affordance. While the step is active the oval now always
  // shows, pulsing until the first usage event lands.
  const showOval = (tokens && tokens.total > 0) || stepActive;
  const label = `Tokens spent in ${PHASE_LABEL[phase] ?? phase}`;
  return (
    <div className="relative h-px flex-1 min-w-[16px] bg-white/[0.06]">
      <motion.div
        initial={{ scaleX: 0 }}
        animate={{ scaleX: active ? 1 : 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="absolute inset-0 origin-left bg-emerald-500/40"
      />
      {showOval && (
        <span
          className={cn(
            "absolute left-1/2 top-0 z-10 -translate-x-1/2 -translate-y-1/2",
            "rounded-full border px-1.5 py-px text-[9px] font-mono leading-none whitespace-nowrap",
            stepActive
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300/90 animate-pulse"
              : active
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300/90"
                : "border-white/[0.08] bg-zinc-900 text-muted-foreground/70",
          )}
          title={
            tokens && tokens.total > 0
              ? `${label}\n` +
                `total: ${tokens.total.toLocaleString()}\n` +
                `input: ${tokens.input.toLocaleString()} · output: ${tokens.output.toLocaleString()}`
              : `${label}\naccounting updates after each model call completes`
          }
        >
          {tokens && tokens.total > 0 ? formatTokens(tokens.total) : "…"}
        </span>
      )}
    </div>
  );
}

// Compact token count: 940 → "940", 12_300 → "12.3k", 4_560_000 → "4.56M".
export function formatTokens(n: number): string {
  if (n < 1_000) return String(n);
  if (n < 1_000_000) return `${(n / 1_000).toFixed(n < 10_000 ? 2 : 1).replace(/\.?0+$/, "")}k`;
  return `${(n / 1_000_000).toFixed(2).replace(/\.?0+$/, "")}M`;
}
