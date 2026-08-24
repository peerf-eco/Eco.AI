"use client";

import { useCallback, useEffect, useMemo, useState, memo, type ReactNode } from "react";
import { motion } from "framer-motion";
import {
  Save, RotateCcw, DraftingCompass, Code2, FlaskConical, ScanEye, Cpu,
  ShieldCheck, Plus, Trash2, Pencil, Check, X, FileSearch, PenLine, Hammer,
  Play, BookOpen, Layers, Globe, Terminal, Info, Bot,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { RagSection } from "./rag-import";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";

const BACKENDS = ["internal", "pi", "codex", "claude", "grok"];
const ROLE_ORDER = ["architect", "coder", "tester", "reviewer"];
const REASONING_LEVELS = ["minimal", "low", "medium", "high", "xhigh"];
const PROVIDERS = [
  "openrouter", "openai", "anthropic", "xai", "groq", "cerebras", "zai",
  "kimi-coding", "minimax", "huggingface", "vercel-ai-gateway",
];

const ROLE_ICONS: Record<string, typeof Code2> = {
  architect: DraftingCompass,
  coder: Code2,
  tester: FlaskConical,
  reviewer: ScanEye,
};

const ROLE_HINTS: Record<string, string> = {
  architect: "Plans the work and pulls marketplace components",
  coder: "Implements sources and builds the artifact",
  tester: "Runs the artifact against acceptance criteria",
  reviewer: "Audits the produced code",
};

interface ModelProfile {
  id: string;
  provider: string;
  reasoning: string;
  temperature?: number | null;
  max_tokens?: number | null;
  provider_pin?: string | null;
}

interface PermissionSpec {
  fs_read: boolean;
  fs_write: boolean;
  build: boolean;
  execute: boolean;
  rag_search: boolean;
  skills: boolean;
  network: boolean;
  commands: string[];
}

interface RoleSetting {
  backend: string;
  model: string;
  reasoning: string;
  prompt?: string | null;
  skill_versions?: Record<string, string>;
  budgets?: Record<string, unknown>;
  permissions?: PermissionSpec;
}

interface LanguageSetting {
  prompt?: string;
  skill_versions?: Record<string, string>;
  eco_wizard?: string;
}

interface ConfigResponse {
  roles?: Record<string, RoleSetting>;
  languages?: Record<string, LanguageSetting>;
  models?: Record<string, ModelProfile>;
  permissions?: {
    defaults?: Partial<PermissionSpec>;
  };
}

const DEFAULT_PERMISSIONS: PermissionSpec = {
  fs_read: true,
  fs_write: true,
  build: true,
  execute: true,
  rag_search: true,
  skills: true,
  network: true,
  commands: ["*"],
};

const PERMISSION_GROUPS = [
  { key: "fs_read", label: "File read", hint: "grep · glob · read across project + marketplace", icon: FileSearch },
  { key: "fs_write", label: "File write", hint: "create and overwrite project files", icon: PenLine },
  { key: "build", label: "Build", hint: "run make on project Makefiles", icon: Hammer },
  { key: "execute", label: "Run binaries", hint: "execute built artifacts", icon: Play },
  { key: "rag_search", label: "RAG search", hint: "semantic marketplace search", icon: BookOpen },
  { key: "skills", label: "Skills", hint: "load on-demand SKILL.md guides", icon: Layers },
  { key: "network", label: "Network", hint: "eco-cli / eco-wizard downloads", icon: Globe },
] as const;

type PermissionKey = (typeof PERMISSION_GROUPS)[number]["key"];

type TabId = "roles" | "models" | "access" | "rag";

const TABS: { id: TabId; label: string; icon: typeof Code2 }[] = [
  { id: "roles", label: "Roles", icon: Code2 },
  { id: "models", label: "Models", icon: Cpu },
  { id: "access", label: "Access", icon: ShieldCheck },
  { id: "rag", label: "RAG", icon: BookOpen },
];

function clonePermissions(value: Partial<PermissionSpec> | undefined): PermissionSpec {
  // Filter to known keys so a server-side schema change can neither crash
  // the panel nor leak unknown fields back into the save payload.
  const source = value || {};
  const known = Object.keys(DEFAULT_PERMISSIONS) as (keyof PermissionSpec)[];
  const filtered: Partial<PermissionSpec> = {};
  for (const key of known) {
    if (key === "commands") continue;
    if (typeof source[key] === "boolean") filtered[key] = source[key];
  }
  filtered.commands = Array.isArray(source.commands) ? [...source.commands] : ["*"];
  return { ...DEFAULT_PERMISSIONS, ...filtered };
}

function canonicalProfile(profile: ModelProfile): string {
  return JSON.stringify([
    profile.id,
    profile.provider,
    profile.reasoning,
    profile.temperature ?? null,
    profile.max_tokens ?? null,
    profile.provider_pin ?? null,
  ]);
}

// Per-role permission overrides are stored as DELTAS over the harness
// defaults (only keys that deviate). Resolving is always
// {...defaults, ...delta}, so untouched keys follow later default changes
// instead of freezing a stale full snapshot at first edit.
function permissionDelta(
  resolved: PermissionSpec,
  defaults: PermissionSpec,
): Partial<PermissionSpec> {
  const delta: Partial<PermissionSpec> = {};
  for (const { key } of PERMISSION_GROUPS) {
    if (resolved[key] !== defaults[key]) delta[key] = resolved[key];
  }
  if (JSON.stringify(resolved.commands) !== JSON.stringify(defaults.commands)) {
    delta.commands = [...resolved.commands];
  }
  return delta;
}

// Seed deltas from the server-resolved role policies (e.g. repo-level
// baselines in roles.yaml), so saves round-trip pre-existing deviations.
function seedOverrides(
  roles: Record<string, RoleSetting>,
  defaults: PermissionSpec,
): Record<string, Partial<PermissionSpec>> {
  const seeded: Record<string, Partial<PermissionSpec>> = {};
  for (const [role, spec] of Object.entries(roles)) {
    const delta = permissionDelta(clonePermissions(spec.permissions), defaults);
    if (Object.keys(delta).length > 0) seeded[role] = delta;
  }
  return seeded;
}

export function AgentSettings() {
  const [tab, setTab] = useState<TabId>("roles");
  const [roles, setRoles] = useState<Record<string, RoleSetting>>({});
  const [languages, setLanguages] = useState<Record<string, LanguageSetting>>({});
  const [models, setModels] = useState<Record<string, ModelProfile>>({});
  // Server-provided model registry snapshot — the diff baseline so saves
  // persist only user-added/edited profiles (plus null markers for deleted
  // ones) and repo-provided config/models.yaml stays authoritative for the
  // untouched entries.
  const [baselineModels, setBaselineModels] = useState<Record<string, ModelProfile>>({});
  const [permDefaults, setPermDefaults] = useState<PermissionSpec>(DEFAULT_PERMISSIONS);
  const [permOverrides, setPermOverrides] = useState<Record<string, Partial<PermissionSpec>>>({});
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [loaded, setLoaded] = useState(false);

  const applyConfig = (body: ConfigResponse) => {
    setRoles(body.roles || {});
    setLanguages(body.languages || {});
    setModels(body.models || {});
    setBaselineModels(body.models || {});
    const defaults = clonePermissions(body.permissions?.defaults);
    setPermDefaults(defaults);
    setPermOverrides(seedOverrides(body.roles || {}, defaults));
    setLoaded(true);
  };

  useEffect(() => {
    fetch(`${API_URL}/config`)
      .then((response) => response.json())
      .then((body: ConfigResponse) => applyConfig(body))
      .catch(() => setStatus("Unable to load agent settings"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const markDirty = () => {
    setDirty(true);
    setStatus("");
  };

  const orderedRoles = useMemo(() => {
    const known = ROLE_ORDER.filter((role) => roles[role]);
    const extras = Object.keys(roles).filter((role) => !ROLE_ORDER.includes(role));
    return [...known, ...extras];
  }, [roles]);

  const modelNames = useMemo(() => Object.keys(models).sort(), [models]);

  // model name → roles using it (single pass; the Models tab renders one
  // lookup per card instead of rescanning all roles per keystroke).
  const modelUsage = useMemo(() => {
    const usage = new Map<string, string[]>();
    for (const [role, spec] of Object.entries(roles)) {
      const list = usage.get(spec.model) || [];
      list.push(role);
      usage.set(spec.model, list);
    }
    return usage;
  }, [roles]);

  const setPermissionDefault = useCallback(
    (key: PermissionKey, value: boolean) => {
      setPermDefaults((current) => {
        const nextDefaults = { ...current, [key]: value };
        // With delta-based overrides, untouched keys automatically follow the
        // new default; only prune explicit overrides this change makes
        // redundant.
        setPermOverrides((overrides) => {
          const next: Record<string, Partial<PermissionSpec>> = {};
          for (const [role, delta] of Object.entries(overrides)) {
            const pruned = { ...delta };
            if (pruned[key] === nextDefaults[key]) delete pruned[key];
            if (Object.keys(pruned).length > 0) next[role] = pruned;
          }
          return next;
        });
        return nextDefaults;
      });
      markDirty();
    },
    [],
  );

  const setRolePermission = useCallback(
    (role: string, key: PermissionKey, value: boolean) => {
      setPermOverrides((current) => {
        const delta = { ...(current[role] || {}) };
        if (value === permDefaults[key]) delete delta[key];
        else delta[key] = value;
        const next = { ...current };
        if (Object.keys(delta).length > 0) next[role] = delta;
        else delete next[role];
        return next;
      });
      markDirty();
    },
    [permDefaults],
  );

  const setRoleCommands = useCallback(
    (role: string, raw: string) => {
      const commands = raw
        .split(",")
        .map((token) => token.trim())
        .filter(Boolean);
      const value = commands.length ? commands : ["*"];
      setPermOverrides((current) => {
        const delta = { ...(current[role] || {}) };
        if (JSON.stringify(value) === JSON.stringify(permDefaults.commands)) delete delta.commands;
        else delta.commands = value;
        const next = { ...current };
        if (Object.keys(delta).length > 0) next[role] = delta;
        else delete next[role];
        return next;
      });
      markDirty();
    },
    [permDefaults],
  );

  const resetRolePermissions = useCallback((role: string) => {
    setPermOverrides((current) => {
      const next = { ...current };
      delete next[role];
      return next;
    });
    markDirty();
  }, []);

  const updateRole = (role: string, patch: Partial<RoleSetting>) => {
    setRoles((current) => ({
      ...current,
      [role]: { ...current[role], ...patch },
    }));
    markDirty();
  };

  const save = async () => {
    setSaving(true);
    setStatus("Saving…");
    try {
      // Roles: only the fields this panel manages — server-derived values
      // (budgets, prompt, skill_versions, resolved permissions) stay
      // authoritative in repo config instead of being pinned by a snapshot.
      const rolePayload = Object.fromEntries(
        Object.entries(roles).map(([role, spec]) => [
          role,
          { backend: spec.backend, model: spec.model, reasoning: spec.reasoning },
        ]),
      );
      // Models: diff against the server baseline — new/edited profiles are
      // persisted, deleted ones are marked null (loader removes them), and
      // untouched repo profiles stay owned by config/models.yaml.
      const modelPayload: Record<string, ModelProfile | null> = {};
      for (const [name, profile] of Object.entries(models)) {
        const baseline = baselineModels[name];
        if (!baseline || canonicalProfile(baseline) !== canonicalProfile(profile)) {
          modelPayload[name] = profile;
        }
      }
      for (const name of Object.keys(baselineModels)) {
        if (!models[name]) modelPayload[name] = null;
      }
      const response = await fetch(`${API_URL}/config/workspace`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          roles: rolePayload,
          languages,
          models: modelPayload,
          permissions: { defaults: permDefaults, roles: permOverrides },
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Unable to save settings");
      setDirty(false);
      setStatus("Saved — applied to new sessions");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to save settings");
    } finally {
      setSaving(false);
    }
  };

  const discard = () => {
    setDirty(false);
    setStatus("");
    setLoaded(false);
    fetch(`${API_URL}/config`)
      .then((response) => response.json())
      .then((body: ConfigResponse) => applyConfig(body))
      .catch(() => setStatus("Unable to reload settings"));
  };

  return (
    <div className="flex flex-col" style={{ minHeight: 0 }}>
      {/* Segmented tabs */}
      <div className="relative flex rounded-xl border border-white/[0.06] bg-black/30 p-1">
        {TABS.map((entry) => (
          <button
            key={entry.id}
            type="button"
            onClick={() => setTab(entry.id)}
            className={cn(
              "relative z-10 flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-[11px] font-medium transition-colors",
              tab === entry.id ? "text-foreground" : "text-muted-foreground hover:text-foreground/80",
            )}
          >
            {tab === entry.id && (
              <motion.span
                layoutId="settings-tab-pill"
                transition={{ type: "spring", stiffness: 500, damping: 35 }}
                className="absolute inset-0 -z-10 rounded-lg border border-white/[0.08] bg-white/[0.07]"
              />
            )}
            <entry.icon className="h-3.5 w-3.5" />
            {entry.label}
          </button>
        ))}
      </div>

      <div className="mt-4 space-y-3">
        {!loaded && !status && (
          <p className="px-1 text-xs text-muted-foreground">Loading configuration…</p>
        )}

        {tab === "roles" && (
          <>
            {orderedRoles.map((role) => (
              <RoleCard
                key={role}
                role={role}
                setting={roles[role]}
                models={models}
                modelNames={modelNames}
                onChange={(patch) => updateRole(role, patch)}
              />
            ))}
            <p className="flex items-start gap-1.5 px-1 text-[11px] leading-relaxed text-muted-foreground/70">
              <Info className="mt-0.5 h-3 w-3 shrink-0" />
              <span>
                Each role can run a different backend and model. Custom IDs like{" "}
                <span className="font-mono text-foreground/70">provider/model</span> are
                accepted without a registry entry.
              </span>
            </p>
          </>
        )}

        {tab === "models" && (
          <ModelsSection
            models={models}
            modelUsage={modelUsage}
            onChange={(next) => {
              setModels(next);
              markDirty();
            }}
          />
        )}

        {tab === "access" && (
          <>
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
              <div className="mb-1 flex items-center gap-2">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-xs font-semibold">Harness defaults</span>
              </div>
              <p className="mb-3 text-[11px] leading-relaxed text-muted-foreground/70">
                Applied to every role. Permissions are bound to roles — models are
                interchangeable, roles define what the agent may touch.
              </p>
              <div className="space-y-2.5">
                {PERMISSION_GROUPS.map((group) => (
                  <div key={group.key} className="flex items-center gap-2.5">
                    <group.icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-medium">{group.label}</div>
                      <div className="truncate text-[10px] text-muted-foreground/60">{group.hint}</div>
                    </div>
                    <Toggle
                      checked={permDefaults[group.key]}
                      onChange={(value) => setPermissionDefault(group.key, value)}
                    />
                  </div>
                ))}
                <div className="flex items-center gap-2.5 pt-1">
                  <Terminal className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium">Command allowlist</div>
                    <div className="truncate text-[10px] text-muted-foreground/60">
                      make targets · artifact names · eco-cli subcommands
                    </div>
                  </div>
                  <Input
                    value={permDefaults.commands.join(", ")}
                    onChange={(event) => {
                      const commands = event.target.value.split(",").map((t) => t.trim()).filter(Boolean);
                      setPermDefaults((current) => ({ ...current, commands: commands.length ? commands : ["*"] }));
                      markDirty();
                    }}
                    placeholder="*"
                    className="h-7 w-28 rounded-lg border-white/[0.08] bg-black/30 px-2 text-center font-mono text-[11px]"
                    aria-label="Default command allowlist"
                  />
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-xs font-semibold">Per-role overrides</span>
                <span className="text-[10px] text-muted-foreground/60">toggle to deviate</span>
              </div>
              <PermissionMatrix
                roles={orderedRoles}
                rolesMeta={roles}
                defaults={permDefaults}
                overrides={permOverrides}
                onToggle={setRolePermission}
                onCommands={setRoleCommands}
                onReset={resetRolePermissions}
              />
              <p className="mt-3 flex items-start gap-1.5 text-[10px] leading-relaxed text-muted-foreground/60">
                <Info className="mt-0.5 h-3 w-3 shrink-0" />
                <span>
                  Enforced for internal backends. External CLI backends
                  (pi/codex/claude/grok — marked <span className="font-mono">ext</span> above)
                  run in their own process with their own tool policy.
                </span>
              </p>
            </div>
          </>
        )}

        {tab === "rag" && <RagSection onImported={markDirty} />}
      </div>

      {/* Sticky save bar */}
      <div className="sticky bottom-0 -mx-5 mt-5 border-t border-white/[0.06] bg-[#0a0a10]/90 px-5 py-3 backdrop-blur-xl">
        <div className="flex items-center gap-2">
          <Button
            type="button"
            size="sm"
            onClick={save}
            disabled={saving || !loaded}
            className="h-8 flex-1 rounded-lg bg-gradient-to-r from-blue-500 to-violet-500 text-xs font-medium text-white shadow-lg shadow-blue-500/20 transition-all hover:from-blue-600 hover:to-violet-600"
          >
            <Save className="mr-1.5 h-3.5 w-3.5" />
            {saving ? "Saving…" : "Save settings"}
          </Button>
          {dirty && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={discard}
              disabled={saving}
              className="h-8 rounded-lg px-2.5 text-xs text-muted-foreground hover:bg-white/[0.06] hover:text-foreground"
            >
              <RotateCcw className="mr-1 h-3 w-3" />
              Discard
            </Button>
          )}
        </div>
        {status && (
          <p className={cn("mt-2 text-[11px]", status.startsWith("Saved") ? "text-emerald-400" : "text-muted-foreground")}>
            {status}
          </p>
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Roles
// ────────────────────────────────────────────────────────────────────────────

function RoleCard({
  role,
  setting,
  models,
  modelNames,
  onChange,
}: {
  role: string;
  setting?: RoleSetting;
  models: Record<string, ModelProfile>;
  modelNames: string[];
  onChange: (patch: Partial<RoleSetting>) => void;
}) {
  const [customizing, setCustomizing] = useState(false);
  const value = setting || { backend: "internal", model: "default", reasoning: "medium" };
  const Icon = ROLE_ICONS[role] || Bot;
  const modelProfile = models[value.model];
  const isCustomModel = value.model && !modelNames.includes(value.model);

  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 transition-colors hover:border-white/[0.1]">
      <div className="mb-2.5 flex items-center gap-2">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-blue-500/20 to-violet-500/20">
          <Icon className="h-3.5 w-3.5 text-blue-300" />
        </div>
        <span className="text-xs font-semibold capitalize">{role}</span>
        {modelProfile && (
          <span className="ml-auto truncate font-mono text-[10px] text-muted-foreground/50" title={modelProfile.id}>
            {modelProfile.id}
          </span>
        )}
      </div>
      <div className="grid grid-cols-3 gap-1.5">
        <label className="sr-only">{`${role} backend`}</label>
        <select
          value={value.backend}
          onChange={(event) => onChange({ backend: event.target.value })}
          className={fieldClass}
          aria-label={`${role} backend`}
        >
          {BACKENDS.map((backend) => (
            <option key={backend} value={backend}>{backend}</option>
          ))}
        </select>
        {customizing ? (
          <Input
            autoFocus
            value={value.model}
            onChange={(event) => onChange({ model: event.target.value })}
            placeholder="provider/model-id"
            className={cn(fieldClass, "font-mono")}
            aria-label={`${role} custom model id`}
            onBlur={() => setCustomizing(false)}
            onKeyDown={(event) => event.key === "Enter" && setCustomizing(false)}
          />
        ) : (
          <select
            value={isCustomModel ? "__custom__" : value.model}
            onChange={(event) => {
              if (event.target.value === "__custom__") setCustomizing(true);
              else onChange({ model: event.target.value });
            }}
            className={fieldClass}
            aria-label={`${role} model`}
          >
            {!modelNames.includes(value.model) && value.model && (
              <option value={value.model}>{value.model} (custom)</option>
            )}
            {modelNames.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
            <option value="__custom__">Custom…</option>
          </select>
        )}
        <select
          value={value.reasoning}
          onChange={(event) => onChange({ reasoning: event.target.value })}
          className={fieldClass}
          aria-label={`${role} reasoning`}
        >
          {REASONING_LEVELS.map((level) => (
            <option key={level} value={level}>{level}</option>
          ))}
        </select>
      </div>
      {ROLE_HINTS[role] && (
        <p className="mt-2 text-[10px] text-muted-foreground/50">{ROLE_HINTS[role]}</p>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Models
// ────────────────────────────────────────────────────────────────────────────

function ModelsSection({
  models,
  modelUsage,
  onChange,
}: {
  models: Record<string, ModelProfile>;
  // model name → roles using it, precomputed by the parent (single pass over
  // roles) so each card renders without rescanning the role map.
  modelUsage: Map<string, string[]>;
  onChange: (next: Record<string, ModelProfile>) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);

  return (
    <>
      {Object.entries(models)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([name, profile]) => (
          <ModelCard
            key={name}
            name={name}
            profile={profile}
            usedBy={modelUsage.get(name) || []}
            editing={editing === name}
            onEdit={(open) => setEditing(open ? name : null)}
            onChange={(next) => onChange({ ...models, [name]: next })}
            onDelete={() => {
              const next = { ...models };
              delete next[name];
              onChange(next);
              setEditing(null);
            }}
          />
        ))}

      {adding ? (
        <ModelForm
          existingNames={Object.keys(models)}
          onCancel={() => setAdding(false)}
          onSubmit={(name, profile) => {
            onChange({ ...models, [name]: profile });
            setAdding(false);
          }}
        />
      ) : (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setAdding(true)}
          className="h-8 w-full rounded-lg border-dashed border-white/[0.12] bg-transparent text-xs text-muted-foreground hover:border-blue-500/40 hover:bg-blue-500/[0.06] hover:text-blue-200"
        >
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Add model
        </Button>
      )}
    </>
  );
}

function ModelCard({
  name,
  profile,
  usedBy,
  editing,
  onEdit,
  onChange,
  onDelete,
}: {
  name: string;
  profile: ModelProfile;
  usedBy: string[];
  editing: boolean;
  onEdit: (open: boolean) => void;
  onChange: (next: ModelProfile) => void;
  onDelete: () => void;
}) {
  const blocked = usedBy.length > 0;
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
      <div className="flex items-center gap-2">
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-violet-500/15">
          <Cpu className="h-3.5 w-3.5 text-violet-300" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-xs font-semibold">{name}</div>
          <div className="truncate font-mono text-[10px] text-muted-foreground/60">{profile.id}</div>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => onEdit(!editing)}
          className="h-7 w-7 rounded-lg hover:bg-white/[0.08]"
          aria-label={`Edit model ${name}`}
        >
          {editing ? <X className="h-3.5 w-3.5" /> : <Pencil className="h-3.5 w-3.5" />}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => { if (!blocked) onDelete(); }}
          disabled={blocked}
          title={blocked ? `In use by: ${usedBy.join(", ")}` : `Remove ${name}`}
          className="h-7 w-7 rounded-lg hover:bg-red-500/10 hover:text-red-400"
          aria-label={`Remove model ${name}`}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        <Badge>{profile.provider}</Badge>
        <Badge>reasoning: {profile.reasoning}</Badge>
        {profile.provider_pin && <Badge accent>{profile.provider_pin}</Badge>}
        {profile.max_tokens != null && <Badge>{profile.max_tokens} tok</Badge>}
      </div>
      {usedBy.length > 0 && (
        <p className="mt-1.5 text-[10px] text-muted-foreground/50">
          used by {usedBy.join(", ")}
        </p>
      )}
      {editing && (
        <div className="mt-3 space-y-2 border-t border-white/[0.06] pt-3">
          <ModelFormFields profile={profile} onChange={onChange} submitLabel="Done" onSubmit={() => onEdit(false)} />
        </div>
      )}
    </div>
  );
}

function ModelForm({
  existingNames,
  onCancel,
  onSubmit,
}: {
  existingNames: string[];
  onCancel: () => void;
  onSubmit: (name: string, profile: ModelProfile) => void;
}) {
  const [name, setName] = useState("");
  const [profile, setProfile] = useState<ModelProfile>({
    id: "",
    provider: "openrouter",
    reasoning: "medium",
    temperature: null,
    max_tokens: null,
    provider_pin: "",
  });
  const valid = name.trim().length > 0 && profile.id.trim().length > 0 && !existingNames.includes(name.trim());

  return (
    <div className="rounded-xl border border-blue-500/25 bg-blue-500/[0.04] p-3">
      <div className="mb-2 text-xs font-semibold text-blue-200">New model profile</div>
      <div className="space-y-2">
        <Input
          autoFocus
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Profile name (e.g. deepseek_r1)"
          className={cn(fieldClass, "h-8")}
          aria-label="Model profile name"
        />
        <ModelFormFields
          profile={profile}
          onChange={setProfile}
          submitLabel="Add model"
          onSubmit={() => valid && onSubmit(name.trim(), { ...profile, provider_pin: profile.provider_pin || null })}
        />
        {!valid && name.trim() && existingNames.includes(name.trim()) && (
          <p className="text-[10px] text-red-400">A profile with this name already exists.</p>
        )}
      </div>
      <button
        type="button"
        onClick={onCancel}
        className="mt-2 text-[11px] text-muted-foreground hover:text-foreground"
      >
        Cancel
      </button>
    </div>
  );
}

function ModelFormFields({
  profile,
  onChange,
  onSubmit,
  submitLabel,
}: {
  profile: ModelProfile;
  onChange: (next: ModelProfile) => void;
  onSubmit: () => void;
  submitLabel: string;
}) {
  return (
    <>
      <Input
        value={profile.id}
        onChange={(event) => onChange({ ...profile, id: event.target.value })}
        placeholder="Model ID (e.g. deepseek/deepseek-r1)"
        className={cn(fieldClass, "h-8 font-mono")}
        aria-label="Model ID"
      />
      <div className="grid grid-cols-2 gap-1.5">
        <select
          value={profile.provider}
          onChange={(event) => onChange({ ...profile, provider: event.target.value })}
          className={fieldClass}
          aria-label="Provider"
        >
          {PROVIDERS.map((provider) => (
            <option key={provider} value={provider}>{provider}</option>
          ))}
        </select>
        <select
          value={profile.reasoning}
          onChange={(event) => onChange({ ...profile, reasoning: event.target.value })}
          className={fieldClass}
          aria-label="Default reasoning"
        >
          {REASONING_LEVELS.map((level) => (
            <option key={level} value={level}>{level}</option>
          ))}
        </select>
      </div>
      <div className="grid grid-cols-3 gap-1.5">
        <Input
          value={profile.provider_pin || ""}
          onChange={(event) => onChange({ ...profile, provider_pin: event.target.value || null })}
          placeholder="PIN"
          className={cn(fieldClass, "h-8 font-mono")}
          aria-label="Provider PIN"
          title="OpenRouter provider routing pin (e.g. tencent, deepseek) — a routing hint, not a secret"
        />
        <Input
          type="number"
          value={profile.max_tokens ?? ""}
          onChange={(event) =>
            onChange({ ...profile, max_tokens: event.target.value ? Number(event.target.value) : null })
          }
          placeholder="Max tok"
          className={cn(fieldClass, "h-8")}
          aria-label="Max tokens"
        />
        <Input
          type="number"
          step="0.1"
          min="0"
          max="2"
          value={profile.temperature ?? ""}
          onChange={(event) =>
            onChange({ ...profile, temperature: event.target.value ? Number(event.target.value) : null })
          }
          placeholder="Temp"
          className={cn(fieldClass, "h-8")}
          aria-label="Temperature"
        />
      </div>
      <Button
        type="button"
        size="sm"
        onClick={onSubmit}
        className="h-7 w-full rounded-lg bg-white/[0.08] text-xs hover:bg-white/[0.14]"
      >
        <Check className="mr-1.5 h-3 w-3" />
        {submitLabel}
      </Button>
    </>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Permissions
// ────────────────────────────────────────────────────────────────────────────

// Memoized: all props are stable between unrelated state changes (handlers are
// useCallback'd in the parent; defaults/overrides change only on edits), so
// typing in another tab does not re-render the roles×groups toggle grid.
const PermissionMatrix = memo(function PermissionMatrix({
  roles,
  rolesMeta,
  defaults,
  overrides,
  onToggle,
  onCommands,
  onReset,
}: {
  roles: string[];
  rolesMeta: Record<string, RoleSetting>;
  defaults: PermissionSpec;
  overrides: Record<string, Partial<PermissionSpec>>;
  onToggle: (role: string, key: PermissionKey, value: boolean) => void;
  onCommands: (role: string, raw: string) => void;
  onReset: (role: string) => void;
}) {
  const resolved = (role: string): PermissionSpec => ({
    ...defaults,
    ...overrides[role],
  });
  return (
    <div className="overflow-x-auto thin-scroll">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="w-24 pb-2 text-left text-[10px] font-medium text-muted-foreground/60">Group</th>
            {roles.map((role) => {
              const external = (rolesMeta[role]?.backend || "internal") !== "internal";
              return (
                <th key={role} className="pb-2 text-center">
                  <div className="flex flex-col items-center gap-0.5">
                    <span className="text-[10px] font-medium capitalize text-muted-foreground">
                      {role}
                      {external && (
                        <span
                          className="ml-1 rounded bg-amber-500/15 px-1 py-px font-mono text-[8px] text-amber-300"
                          title="External CLI backend — permissions enforced for internal backends only"
                        >
                          ext
                        </span>
                      )}
                    </span>
                    {overrides[role] && (
                      <button
                        type="button"
                        onClick={() => onReset(role)}
                        title="Reset to harness defaults"
                        className="text-[9px] text-blue-400/80 hover:text-blue-300"
                      >
                        reset
                      </button>
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {PERMISSION_GROUPS.map((group) => (
            <tr key={group.key} className="border-t border-white/[0.04]">
              <td className="py-1.5 pr-2">
                <div className="flex items-center gap-1.5" title={group.hint}>
                  <group.icon className="h-3 w-3 shrink-0 text-muted-foreground/70" />
                  <span className="truncate text-[10px]">{group.label}</span>
                </div>
              </td>
              {roles.map((role) => (
                <td key={role} className="py-1.5 text-center">
                  <Toggle
                    small
                    checked={resolved(role)[group.key]}
                    onChange={(value) => onToggle(role, group.key, value)}
                    ariaLabel={`${role} ${group.label}`}
                  />
                </td>
              ))}
            </tr>
          ))}
          <tr className="border-t border-white/[0.04]">
            <td className="py-2 pr-2">
              <div className="flex items-center gap-1.5" title="Command allowlist for this role">
                <Terminal className="h-3 w-3 shrink-0 text-muted-foreground/70" />
                <span className="truncate text-[10px]">Commands</span>
              </div>
            </td>
            {roles.map((role) => (
              <td key={role} className="py-2 text-center" colSpan={1}>
                <Input
                  value={(overrides[role]?.commands || defaults.commands).join(",")}
                  onChange={(event) => onCommands(role, event.target.value)}
                  className="h-6 w-full min-w-16 rounded-md border-white/[0.08] bg-black/30 px-1 text-center font-mono text-[10px]"
                  aria-label={`${role} commands`}
                />
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
});

// ────────────────────────────────────────────────────────────────────────────
// Primitives
// ────────────────────────────────────────────────────────────────────────────

const fieldClass =
  "h-8 w-full rounded-lg border border-white/[0.08] bg-black/30 px-2 text-xs text-foreground outline-none transition-colors focus:border-blue-500/40";

function Badge({ children, accent }: { children: ReactNode; accent?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium",
        accent
          ? "bg-amber-500/15 text-amber-300"
          : "bg-white/[0.06] text-muted-foreground",
      )}
    >
      {children}
    </span>
  );
}

function Toggle({
  checked,
  onChange,
  small,
  disabled,
  ariaLabel,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  small?: boolean;
  disabled?: boolean;
  ariaLabel?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative flex shrink-0 items-center rounded-full px-0.5 transition-colors duration-200",
        small ? "h-4 w-7" : "h-5 w-9",
        checked ? "justify-end bg-blue-500/80" : "justify-start bg-white/[0.12]",
        disabled && "cursor-not-allowed opacity-40",
      )}
    >
      <motion.span
        layout
        transition={{ type: "spring", stiffness: 550, damping: 32 }}
        className={cn(
          "rounded-full bg-white shadow-sm",
          small ? "h-3 w-3" : "h-4 w-4",
        )}
      />
    </button>
  );
}
