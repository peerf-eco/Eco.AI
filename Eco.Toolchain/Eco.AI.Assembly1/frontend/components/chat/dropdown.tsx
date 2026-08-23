"use client";

import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DropdownOption<T extends string> {
  value: T;
  label: string;
}

interface DropdownProps<T extends string> {
  value: T;
  options: readonly DropdownOption<T>[];
  onChange: (value: T) => void;
  icon?: ReactNode;
  disabled?: boolean;
  title?: string;
  className?: string;
}

// Shared selector pill used across the chat input dock. The menu floats
// upward (bottom-full) because the trigger row sits at the bottom of the
// input frame, and renders near-black with white text so every option is
// readable regardless of page-level theming.
export function Dropdown<T extends string>({
  value,
  options,
  onChange,
  icon,
  disabled,
  title,
  className,
}: DropdownProps<T>) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={wrapperRef} className={cn("relative", className)}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        title={title}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={cn(
          "flex max-w-[180px] items-center gap-1.5 rounded-full px-2.5 py-1.5 text-xs",
          "bg-white/[0.05] border border-white/[0.08]",
          "hover:bg-white/[0.09] hover:border-white/[0.14]",
          "transition-colors text-foreground/90",
          open && "bg-white/[0.09] border-blue-500/30",
          disabled && "opacity-50 cursor-not-allowed hover:bg-white/[0.05]",
        )}
      >
        {icon}
        <span className="truncate font-mono">{options.find((o) => o.value === value)?.label ?? value}</span>
        <ChevronDown
          className={cn(
            "h-3 w-3 shrink-0 text-muted-foreground transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>
      {open && (
        <div
          role="listbox"
          className={cn(
            "absolute bottom-full mb-2 left-0 z-40 min-w-[150px] max-h-64 overflow-y-auto",
            "rounded-xl border border-white/10 bg-[#0b0b0f]/[0.97] backdrop-blur-xl",
            "shadow-[0_16px_48px_-12px_rgba(0,0,0,0.8)] p-1.5 space-y-0.5",
          )}
        >
          {options.map((option) => {
            const active = option.value === value;
            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={active}
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center justify-between gap-3 rounded-lg px-2.5 py-1.5",
                  "text-left text-xs text-white transition-colors",
                  "hover:bg-white/10",
                  active && "bg-blue-500/20 text-white",
                )}
              >
                <span className="truncate font-mono">{option.label}</span>
                {active && <Check className="h-3 w-3 shrink-0 text-blue-300" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
