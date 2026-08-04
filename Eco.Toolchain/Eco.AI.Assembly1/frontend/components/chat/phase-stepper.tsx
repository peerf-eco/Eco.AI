"use client";

import { CheckCircle2, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  PHASE_LABEL,
  STEPPER_PHASES,
  type HarnessPhase,
} from "./types";

interface PhaseStepperProps {
  currentPhase: HarnessPhase | null;
  completedPhases: HarnessPhase[];
}

type StepState = "pending" | "active" | "completed";

function stepState(phase: HarnessPhase, current: HarnessPhase | null, completed: HarnessPhase[]): StepState {
  if (completed.includes(phase)) return "completed";
  // awaiting_approval visually still belongs to Planning.
  if (current === phase) return "active";
  if (current === "awaiting_approval" && phase === "planning") return "active";
  return "pending";
}

export function PhaseStepper({ currentPhase, completedPhases }: PhaseStepperProps) {
  return (
    <div className="flex items-center gap-2 px-6 py-3 glass border-b border-white/[0.06]">
      {STEPPER_PHASES.map((phase, i) => {
        const state = stepState(phase, currentPhase, completedPhases);
        const isLast = i === STEPPER_PHASES.length - 1;
        return (
          <div key={phase} className="flex items-center gap-2 flex-1 last:flex-initial">
            <StepDot phase={phase} state={state} index={i} />
            {!isLast && <Connector active={state === "completed"} />}
          </div>
        );
      })}
    </div>
  );
}

interface StepDotProps {
  phase: HarnessPhase;
  state: StepState;
  index: number;
}

function StepDot({ phase, state, index }: StepDotProps) {
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
        {PHASE_LABEL[phase]}
      </span>
    </div>
  );
}

function Connector({ active }: { active: boolean }) {
  return (
    <div className="relative h-px flex-1 min-w-[16px] bg-white/[0.06]">
      <motion.div
        initial={{ scaleX: 0 }}
        animate={{ scaleX: active ? 1 : 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="absolute inset-0 origin-left bg-emerald-500/40"
      />
    </div>
  );
}
