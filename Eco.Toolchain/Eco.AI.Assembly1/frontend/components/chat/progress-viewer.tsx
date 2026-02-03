import React from "react";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type Stage = 
  | "analyze_request"
  | "select_components"
  | "retrieve_context"
  | "generate_code"
  | "review_code"
  | "complete";

interface ProgressViewerProps {
  currentStage: Stage;
  isProcessing: boolean;
}

const STAGES: { id: Stage; label: string }[] = [
  { id: "analyze_request", label: "Analysis" },
  { id: "select_components", label: "Selection" },
  { id: "retrieve_context", label: "Retrieval (RAG)" },
  { id: "generate_code", label: "Generation" },
  { id: "review_code", label: "Review" },
];

export function ProgressViewer({ currentStage, isProcessing }: ProgressViewerProps) {
  // Определяем индекс текущей стадии
  const currentIndex = STAGES.findIndex((s) => s.id === currentStage);
  // Если complete, то все стадии пройдены
  const activeIndex = currentStage === "complete" ? STAGES.length : currentIndex;

  return (
    <div className="w-full py-4">
      <div className="relative flex justify-between">
        {/* Линия прогресса фона */}
        <div className="absolute left-0 top-1/2 -z-10 h-0.5 w-full -translate-y-1/2 bg-secondary" />
        
        {/* Активная линия прогресса */}
        <div 
          className="absolute left-0 top-1/2 -z-10 h-0.5 -translate-y-1/2 bg-primary transition-all duration-500 ease-in-out"
          style={{ width: `${(activeIndex / (STAGES.length - 1)) * 100}%` }}
        />

        {STAGES.map((stage, index) => {
          const isCompleted = index < activeIndex;
          const isActive = index === activeIndex;
          
          return (
            <div key={stage.id} className="flex flex-col items-center bg-background px-2">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border-2 transition-all duration-300",
                  isCompleted
                    ? "border-primary bg-primary text-primary-foreground"
                    : isActive
                    ? "border-primary text-primary ring-4 ring-primary/20"
                    : "border-muted-foreground text-muted-foreground"
                )}
              >
                {isCompleted ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : isActive && isProcessing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Circle className="h-4 w-4" />
                )}
              </div>
              <span
                className={cn(
                  "mt-2 text-xs font-medium transition-colors",
                  isActive || isCompleted ? "text-foreground" : "text-muted-foreground"
                )}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

