# ALLOW_PLAN — Chat rendering & tool-approval hardening

Plan titles for the issues identified during the reasoning-trace / tool-approval
review. Gap #1 (dropped `node_event` error) is already fixed in code; the items
below are the remaining ones, each stated as a plan title with the cleanest fix.

---

## PLAN-1 — Split model answer from reasoning (fix gap #2)

**Problem:** `use-harness-socket.ts` appends both `thinking_delta` and
`text_delta` into `type:"thinking"` blocks. The model's actual answer therefore
renders inside a collapsible reasoning block that closes when `isActive` flips
to false (`thinking-block.tsx:21-24`), so in CHAT / one-shot modes the answer
is hidden by default and indistinguishable from reasoning.

**Cleanest fix:** Route the two delta kinds to separate block types.
- `thinking_delta` → existing `thinking` block (collapsible, greyed).
- `text_delta` → a new `answer` block that is **always expanded**, uses normal
  prose styling (not the reasoning caret/pulse), and is finalised like the
  thinking block on tool/phase boundaries.
- Update `StreamMessage` (`stream-message.tsx`) with a `case "answer"` branch
  and add `answer` to the `StreamBlock` union in `types.ts`.

This keeps reasoning traces intact while making the final answer first-class and
always visible.

---

## PLAN-2 — Emit structured build/test/escalation events (fix gap #3)

**Problem:** Frontend already has handlers for `node_done`, `build_fail`,
`test_fail`, and `escalation_required` (`use-harness-socket.ts`), but the
backend (`server.py`) never emits these types — only `node_event`,
`phase_change`, `pipeline_done`, `plan_review_required`, `worktree_created`,
`heartbeat`, `error`. So build/test/escalation outcomes surface only as a bare
`pipeline_done(status=failed)` + `tester_report_md`, and the dedicated cards are
dead code.

**Cleanest fix (two coordinated steps):**
1. **Backend:** In the coder/tester sub-orchestrator paths, emit real events —
   `build_fail` (with `error_md` + `retry_count`), `test_fail` (with
   `reason_md` + `retry_count`), and `escalation_required` (with the already
   collected `reason`/`build_log`/`tester_report_md`/`plan_md`/`coder_summary_md`)
   — instead of folding everything into `pipeline_done`. Keep `pipeline_done`
   for the terminal summary.
2. **Frontend:** Keep the existing `build_fail`/`test_fail`/`escalation_required`
   branches (they already map to the right props); add a `node_done` emit on
   agent handoff if a richer summary card is wanted, otherwise drop the unused
   `node_done` handler to avoid dead code.

Result: failures get dedicated, scannable cards instead of being buried in a
single failed status line.

---

## PLAN-3 — Surface tool-denial notices to the user (tool-approval visibility)

**Context:** Tool approvals are a hardcoded code allowlist (`_ALLOWED_SUBCOMMANDS`
in `agent/internal/tools/eco_cli.py`) and path allowlists (`_is_within_ni`).
A disallowed action is **silently applied** as a tool error returned to the
model — there is intentionally **no interactive user-permission prompt**. That
is a sound safety default, but the denial is currently only visible inside the
agent's tool-card output, easy to miss.

**Cleanest fix:** When a tool call ends with `is_error` and the error text
matches a known denial pattern (whitelist/subcommand rejection or "outside the
allowed roots"), upgrade the tool card with a distinct "blocked by policy"
badge/explanation and optionally append a one-line system note block so the user
sees *why* the agent was stopped, without changing the allowlist behaviour.

> Out of scope unless requested: making disallowed tools **interactive**
> (prompt the user to approve). That would require a new
> `tool_approval_required` WS event + a frontend approve/deny dialog and a
> stateful pause in the agent loop — a larger change to both backend and agent.

---

## Summary of priorities
1. **PLAN-1** — highest UX impact (answers are currently hidden).
2. **PLAN-2** — medium; improves failure diagnosability.
3. **PLAN-3** — low/optional; polish on an already-safe allowlist design.
