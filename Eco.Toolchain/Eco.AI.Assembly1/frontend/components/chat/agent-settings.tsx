"use client";

import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";
const BACKENDS = ["internal", "pi", "codex", "claude"];
const ROLES = ["architect", "coder", "tester"];

interface RoleSetting {
  backend: string;
  model: string;
  reasoning: string;
}

interface LanguageSetting {
  prompt?: string;
  skill_versions?: Record<string, string>;
  eco_wizard?: string;
}

export function AgentSettings() {
  const [roles, setRoles] = useState<Record<string, RoleSetting>>({});
  const [languages, setLanguages] = useState<Record<string, LanguageSetting>>({});
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/config`)
      .then((response) => response.json())
      .then((body) => {
        setRoles(body.roles || {});
        setLanguages(body.languages || {});
      })
      .catch(() => setStatus("Unable to load agent settings"));
  }, []);

  const update = (role: string, key: keyof RoleSetting, value: string) => {
    setRoles((current) => ({
      ...current,
      [role]: { ...(current[role] || { backend: "internal", model: "default", reasoning: "medium" }), [key]: value },
    }));
  };

  const updateLanguageSkill = (language: string, value: string) => {
    setLanguages((current) => ({
      ...current,
      [language]: {
        ...(current[language] || {}),
        skill_versions: {
          ...(current[language]?.skill_versions || {}),
          language: value,
        },
      },
    }));
  };

  const save = async () => {
    setStatus("Saving…");
    try {
      const response = await fetch(`${API_URL}/config/workspace`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roles, languages }),
      });
      if (!response.ok) throw new Error("Unable to save settings");
      setStatus("Saved for this workspace");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to save settings");
    }
  };

  return (
    <div className="space-y-3">
      {ROLES.map((role) => {
        const setting = roles[role] || { backend: "internal", model: "default", reasoning: "medium" };
        return (
          <div key={role} className="rounded-lg border border-white/[0.06] p-3 space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{role}</div>
            <div className="grid grid-cols-3 gap-2">
              <select
                value={setting.backend}
                onChange={(event) => update(role, "backend", event.target.value)}
                className="rounded-md border border-white/[0.08] bg-black/20 px-2 py-1.5 text-xs"
                aria-label={`${role} backend`}
              >
                {BACKENDS.map((backend) => <option key={backend}>{backend}</option>)}
              </select>
              <Input
                value={setting.model}
                onChange={(event) => update(role, "model", event.target.value)}
                placeholder="model profile"
                className="h-8 text-xs"
                aria-label={`${role} model`}
              />
              <select
                value={setting.reasoning}
                onChange={(event) => update(role, "reasoning", event.target.value)}
                className="rounded-md border border-white/[0.08] bg-black/20 px-2 py-1.5 text-xs"
                aria-label={`${role} reasoning`}
              >
                {["minimal", "low", "medium", "high", "xhigh"].map((level) => <option key={level}>{level}</option>)}
              </select>
            </div>
          </div>
        );
      })}
      <div className="rounded-lg border border-white/[0.06] p-3 space-y-2">
        <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Language skills</div>
        {["C", "CPP", "Python", "Java"].map((language) => (
          <div key={language} className="grid grid-cols-[70px_1fr] items-center gap-2">
            <span className="text-xs font-mono">{language}</span>
            <Input
              value={languages[language]?.skill_versions?.language || "1"}
              onChange={(event) => updateLanguageSkill(language, event.target.value)}
              placeholder="skill version"
              className="h-8 text-xs"
              aria-label={`${language} skill version`}
            />
          </div>
        ))}
      </div>
      <Button type="button" size="sm" onClick={save}>
        <Save className="mr-2 h-3.5 w-3.5" />
        Save workspace settings
      </Button>
      {status && <p className="text-xs text-muted-foreground">{status}</p>}
    </div>
  );
}