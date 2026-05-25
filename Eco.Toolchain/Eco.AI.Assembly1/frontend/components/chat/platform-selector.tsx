"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";

// What we send to the backend (eco-cli `-o` and `-a` flag values, validated
// by the marketplace CLI). Keep this list aligned with what eco-cli accepts:
// see SKILL.md → "Supported OS values" and "Supported architectures".
export interface PlatformOption {
  os: string;
  arch: string;
  label: string;
}

export const PLATFORM_OPTIONS: PlatformOption[] = [
  { os: "Linux",   arch: "x86_64", label: "Linux · x86_64" },
  { os: "Windows", arch: "x86_64", label: "Windows · x86_64" },
  { os: "Linux",   arch: "arm64",  label: "Linux · arm64" },
  { os: "macOS",   arch: "arm64",  label: "macOS · arm64" },
];

export const DEFAULT_PLATFORM = PLATFORM_OPTIONS[0];

interface PlatformSelectorProps {
  value: PlatformOption;
  onChange: (p: PlatformOption) => void;
  disabled?: boolean;
}

export function PlatformSelector({ value, onChange, disabled }: PlatformSelectorProps) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Close on outside-click. We keep this local instead of using a Radix
  // popover — the menu is tiny and we want it to share the input row's
  // visual rhythm without dragging in extra portal layers.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
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
        onClick={() => setOpen((v) => !v)}
        title="Target platform for the built component"
        className={cn(
          "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs",
          "bg-white/[0.04] border border-white/[0.06]",
          "hover:bg-white/[0.08] hover:border-white/[0.12]",
          "transition-colors text-foreground/80",
          disabled && "opacity-50 cursor-not-allowed hover:bg-white/[0.04]",
        )}
      >
        <Cpu className="h-3 w-3 text-blue-400" />
        <span className="font-mono">{value.label}</span>
        <ChevronDown className={cn("h-3 w-3 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="absolute bottom-full mb-2 left-0 z-30 min-w-[200px] rounded-lg glass-strong border border-white/[0.08] shadow-2xl p-1">
          {PLATFORM_OPTIONS.map((opt) => {
            const active = opt.os === value.os && opt.arch === value.arch;
            return (
              <button
                key={`${opt.os}-${opt.arch}`}
                type="button"
                onClick={() => {
                  onChange(opt);
                  setOpen(false);
                }}
                className={cn(
                  "w-full text-left px-2.5 py-1.5 rounded text-xs font-mono",
                  "hover:bg-white/[0.06] transition-colors",
                  active && "bg-blue-500/10 text-blue-200",
                )}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
