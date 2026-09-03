"use client";

import { Code2 } from "lucide-react";
import { Dropdown, type DropdownOption } from "./dropdown";

export const LANGUAGE_OPTIONS = ["C", "CPP", "Python", "Java"] as const;
export type ProgrammingLanguage = (typeof LANGUAGE_OPTIONS)[number];

const DROPDOWN_OPTIONS: DropdownOption<ProgrammingLanguage>[] = LANGUAGE_OPTIONS.map(
  (language) => ({ value: language, label: language }),
);

interface LanguageSelectorProps {
  value: ProgrammingLanguage;
  onChange: (language: ProgrammingLanguage) => void;
  disabled?: boolean;
}

export function LanguageSelector({ value, onChange, disabled }: LanguageSelectorProps) {
  return (
    <Dropdown
      value={value}
      options={DROPDOWN_OPTIONS}
      onChange={onChange}
      icon={<Code2 className="h-3 w-3 shrink-0 text-violet-400" />}
      disabled={disabled}
      title="Programming language for the generated project"
    />
  );
}
