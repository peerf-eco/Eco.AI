"use client";

import { Cpu } from "lucide-react";
import { Dropdown, type DropdownOption } from "./dropdown";

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

const DROPDOWN_OPTIONS: DropdownOption<string>[] = PLATFORM_OPTIONS.map(
  (platform) => ({ value: platform.label, label: platform.label }),
);

interface PlatformSelectorProps {
  value: PlatformOption;
  onChange: (p: PlatformOption) => void;
  disabled?: boolean;
}

export function PlatformSelector({ value, onChange, disabled }: PlatformSelectorProps) {
  return (
    <Dropdown
      value={value.label}
      options={DROPDOWN_OPTIONS}
      onChange={(label) => {
        const match = PLATFORM_OPTIONS.find((p) => p.label === label);
        if (match) onChange(match);
      }}
      icon={<Cpu className="h-3 w-3 shrink-0 text-blue-400" />}
      disabled={disabled}
      title="Target platform for the built component"
    />
  );
}
