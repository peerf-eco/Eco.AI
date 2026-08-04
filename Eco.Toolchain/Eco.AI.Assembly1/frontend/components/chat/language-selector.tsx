"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Code2 } from "lucide-react";
import { cn } from "@/lib/utils";

export const LANGUAGE_OPTIONS = ["C", "CPP", "Python", "Java"] as const;
export type ProgrammingLanguage = (typeof LANGUAGE_OPTIONS)[number];

interface LanguageSelectorProps {
  value: ProgrammingLanguage;
  onChange: (language: ProgrammingLanguage) => void;
  disabled?: boolean;
}

export function LanguageSelector({ value, onChange, disabled }: LanguageSelectorProps) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
        title="Programming language for the generated project"
        className={cn(
          "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs",
          "bg-white/[0.04] border border-white/[0.06]",
          "hover:bg-white/[0.08] hover:border-white/[0.12]",
          "transition-colors text-foreground/80",
          disabled && "opacity-50 cursor-not-allowed",
        )}
      >
        <Code2 className="h-3 w-3 text-violet-400" />
        <span className="font-mono">{value}</span>
        <ChevronDown className={cn("h-3 w-3 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="absolute bottom-full mb-2 left-0 z-30 min-w-[130px] rounded-lg glass-strong border border-white/[0.08] shadow-2xl p-1">
          {LANGUAGE_OPTIONS.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => {
                onChange(option);
                setOpen(false);
              }}
              className={cn(
                "w-full text-left px-2.5 py-1.5 rounded text-xs font-mono",
                "hover:bg-white/[0.06] transition-colors",
                option === value && "bg-violet-500/10 text-violet-200",
              )}
            >
              {option}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}