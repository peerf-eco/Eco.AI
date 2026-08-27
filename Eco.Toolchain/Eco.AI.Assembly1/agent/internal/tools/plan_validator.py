"""Closed-plan validator for the architect role (ACOM conventions).

Wired into the architect's `to_coder` stop-tool through the EcoAgent
`before_tool_call` gate so a non-closed plan cannot be handed off to the
coder. It catches the regressions the ACOM rules forbid:

* inventing `IEcoMemoryManager1.GetAllocator` (the method does not exist —
  the allocator is obtained via `QueryInterface`);
* treating `Eco.System1` as a bus-registered ACOM component (it is a
  statically-linked system *library* with no CID and no factory symbol);
* omitting the explicit bootstrap chain
  `EcoMain -> QueryInterface(GID_IEcoSystem) -> IEcoSystem1 ->
   QueryInterface(IID_IEcoInterfaceBus1) -> IEcoInterfaceBus1`;
* missing the `=== Target triple ===` block (OS / arch / build_variant
  come from the chat-frame UI; the architect must copy them into the
  plan and FAIL when the user did not provide them);
* handing off more than ``HARNESS_PLAN_HANDOFF_MAX_BYTES`` to the coder
  (this caused the `chat-1ca5b8f4` coder 400 — the previous version
  re-stitched the whole architect context into the coder prompt and
  crashed the provider's 262 144-token limit);
* confusing an IID (e.g. `…424E5553`, `BNUS`) for a CID (the real
  `Eco.InterfaceBus1` CID is `…42757331`) — the `chat-8fc99e0c` plan
  shipped a wrong CID for InterfaceBus1 and would have failed at link
  time in the coder. The filesystem-level check in
  ``_check_cid_against_lib_filenames`` (architect.py) cross-checks
  every CID against ``lib<CID>.a`` filenames in the marketplace
  cache for the chosen target triple — that's the load-bearing
  check; this file's text-only check is a soft warning;
* mentioning docs/specs/*.md paths without specifying the new
  component name in the New Component table (the parallel-coder
  spec-file contract).

Severity:
* ``block`` — handoff is refused; the model must fix the plan and call
  `to_coder` again.
* ``warn``  — advisory; the handoff proceeds but the issue is reported.

Note: "foreign `HeaderFiles/`/`SourceFiles/` read of a dependency" is enforced
by the tool-permission layer (read-only roots) plus the role instructions, not
by this text validator.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass
class Violation:
    severity: str  # "block" | "warn"
    message: str


# "System1" in ASCII hex = 53 79 73 74 65 6D 31 — a System1 CID/factory suffix.
_SYSTEM1_HEX = "537973656D31"

_GETALLOC_CALL = re.compile(r"GetAllocator\s*\(|->GetAllocator|\.GetAllocator")
_CID_SYSTEM1 = re.compile(r"CID_EcoSystem1")
_SYSTEM1_CID_HEX = re.compile(_SYSTEM1_HEX, re.IGNORECASE)
_FACTORY_SYSTEM1 = re.compile(
    r"GetIEcoComponentFactoryPtr_[0-9A-Fa-f]{0,32}" + _SYSTEM1_HEX, re.IGNORECASE
)
_REGISTER_SYSTEM1 = re.compile(r"RegisterComponent\s*\([^)]*Eco\.System1")
_QUERY_SYSTEM1 = re.compile(r"QueryComponent\s*\([^)]*Eco\.System1")
_BOOTSTRAP_TOKENS = ("EcoMain", "GID_IEcoSystem", "IID_IEcoInterfaceBus1")
_SUCCESES_TYPO = re.compile(r"ERR_ECO_SUCCESES")
# Target-triple block. Required so the plan does not invent the OS/arch.
#
# Accepts any heading whose first non-whitespace word after "##" is
# "Target" — case-insensitive, with or without a trailing colon, with
# or without a clarifying parenthetical ("(verbatim from seed)").
# The strict end-anchor previously rejected valid paraphrases and forced
# the architect to re-emit the plan with no semantic change.
# (Bug history: ses-6acd93e6 turn 4 was blocked for "## Target triple
# (verbatim from seed)" and turn 8 re-emitted with the exact form
# required, wasting 2 turns and ~22 K reasoning tokens.)
_TARGET_TRIPLE = re.compile(
    r"^##\s*[Tt]arget\s+[Tt]riple\b[^\n]*$",
    re.MULTILINE,
)
# 32-hex CID with optional underscores around it (table cells often write
# `000000000000000000000000XXXXXXXX`). The validator looks at the
# trailing 8 hex chars to detect an IID-as-CID confusion: an IID is
# not a CID, but the model has been seen to paste one where the other
# belongs.
_CID_FULL = re.compile(r"(?<![0-9A-Fa-f])0*([0-9A-Fa-f]{8})(?![0-9A-Fa-f])")
# Spec-path reference: docs/specs/<Name>.md. The component name must be
# an `Eco...` PascalCase identifier so the spec is unambiguously a
# new ACOM component spec (and not e.g. a typo'd reference).
_SPEC_PATH_RE = re.compile(
    r"docs/specs/(?P<name>[A-Za-z0-9_.\-]+)\.md"
)
# Handoff budget. The provider limit is 262 144 tokens and the static
# system prompt + tool contract + seed already occupy ~30K-40K; leaving
# the architect <= plan_handoff_max_bytes of markdown is a safe ceiling
# that leaves room for the coder's own tool-output history.
#
# Default 8 KB matches the rule-of-thumb used in the `chat-1ca5b8f4`
# Celsius->Fahrenheit post-mortem. The harness config layer exposes the
# same value (`HarnessConfig.plan_handoff_max_bytes`, override via
# `HARNESS_PLAN_HANDOFF_MAX_BYTES`); we read the env var here because
# the validator is a free function called from a stop-tool gate (not
# constructed by `load_config`).
_DEFAULT_HANDOFF_MAX_BYTES = 8 * 1024


def _handoff_max_bytes() -> int:
    raw = os.getenv("HARNESS_PLAN_HANDOFF_MAX_BYTES")
    if raw is None or not raw.strip():
        return _DEFAULT_HANDOFF_MAX_BYTES
    try:
        value = int(raw.strip())
    except ValueError:
        return _DEFAULT_HANDOFF_MAX_BYTES
    return value if value > 0 else _DEFAULT_HANDOFF_MAX_BYTES


def validate_closed_plan(plan: str) -> list[Violation]:
    """Return all violations found in the architect's plan text."""
    vios: list[Violation] = []
    if not plan or not plan.strip():
        return [Violation("block", "Plan is empty — nothing was handed off.")]

    # --- Hard: invented GetAllocator call -----------------------------------
    if _GETALLOC_CALL.search(plan):
        vios.append(Violation(
            "block",
            "Plan calls `GetAllocator` on IEcoMemoryManager1. That method does not "
            "exist — obtain IEcoMemoryAllocator1 via QueryInterface (never GetAllocator).",
        ))

    # --- Hard: Eco.System1 treated as a component (CID / factory / bus) ------
    if _CID_SYSTEM1.search(plan):
        vios.append(Violation(
            "block",
            "Plan references `CID_EcoSystem1`. Eco.System1 is a system library with no "
            "CID — never search for or register a System1 CID/factory.",
        ))
    if _SYSTEM1_CID_HEX.search(plan):
        vios.append(Violation(
            "block",
            "Plan contains a System1 CID/factory symbol (…537973656D31). Eco.System1 has "
            "no CID/factory and is never registered on the bus.",
        ))
    if _FACTORY_SYSTEM1.search(plan):
        vios.append(Violation(
            "block",
            "Plan uses a `GetIEcoComponentFactoryPtr_*` symbol for Eco.System1. It is a "
            "linked library, not an ACOM component — no factory exists.",
        ))
    if _REGISTER_SYSTEM1.search(plan) or _QUERY_SYSTEM1.search(plan):
        vios.append(Violation(
            "block",
            "Plan registers/queries Eco.System1 on the interface bus. Eco.System1 is a "
            "statically-linked library (no CID) and must not appear in RegisterComponent/QueryComponent.",
        ))

    # --- Hard: explicit bootstrap chain --------------------------------------
    missing = [t for t in _BOOTSTRAP_TOKENS if t not in plan]
    if missing:
        vios.append(Violation(
            "block",
            "Bootstrap chain incomplete — missing: " + ", ".join(missing) + ". The plan "
            "must show EcoMain -> QueryInterface(GID_IEcoSystem) -> IEcoSystem1 -> "
            "QueryInterface(IID_IEcoInterfaceBus1) -> IEcoInterfaceBus1.",
        ))

    # --- Hard: target triple block present -----------------------------------
    if not _TARGET_TRIPLE.search(plan):
        vios.append(Violation(
            "block",
            "Plan is missing a `## Target triple` section. Copy the three user-selected "
            "values (OS, arch, build_variant) from the seed; the coder needs the literal "
            ".a path and the GID_IEcoSystem_<arch> macro, both derived from the triple.",
        ))

    # --- Hard: handoff size budget -------------------------------------------
    handoff_max = _handoff_max_bytes()
    handoff_len = len(plan.encode("utf-8"))
    if handoff_len > handoff_max:
        vios.append(Violation(
            "block",
            f"Plan is {handoff_len} bytes — over the {handoff_max}-byte "
            "budget (HARNESS_PLAN_HANDOFF_MAX_BYTES) that keeps the coder under the "
            "262K-token provider limit. Drop the per-component .a filename columns (the "
            "coder inherits them from the seed's Pre-resolved identifiers block) and "
            "quote only the one prior-art line that is non-obvious. If still over budget, "
            "split the task with the user.",
        ))

    # --- Soft: IID/CID overlap (chat-8fc99e0c regression warning) ---------
    # ACOM convention is that a component's CID and the IID of its main
    # interface often share the trailing 8 hex (last 4 bytes), so a
    # naive tail-equality check would over-fire. We only WARN on the
    # overlap and rely on the filesystem-level CID-vs-.a-filename check
    # in _plan_gate (architect.py) to catch the real bug — when a CID in
    # the plan does not exist as a `lib<CID>.a` filename in the
    # marketplace cache for the chosen target triple.
    cid_8hex = {m.group(1).upper() for m in _CID_FULL.finditer(plan)}
    iid_8hex = set()
    for m in re.finditer(
        r"IID_[A-Za-z0-9_]+\s*=\s*\{0x01,\s*0x10,\s*\{[^}]*\}\}",
        plan,
    ):
        all_bytes = re.findall(r"0x[0-9A-Fa-f]{2}", m.group(0))
        if len(all_bytes) >= 4:
            last4 = all_bytes[-4:]
            iid_8hex.add("".join(b[2:].upper() for b in last4))
    collisions = cid_8hex & iid_8hex
    if collisions:
        cited = [f"…{hex8}" for hex8 in sorted(collisions)]
        vios.append(Violation(
            "warn",
            "Plan has CIDs and IIDs sharing the trailing 8 hex (" + ", ".join(cited) + "). "
            "This is normal in ACOM (a component's CID and its main interface's IID "
            "frequently share the last 4 bytes). The hard check is the filesystem-level "
            "CID-vs-.a-filename cross-check in architect.py — every CID you listed MUST "
            "exist as `lib<CID>.a` under "
            "`marketplace_cache/<Name>/BuildFiles/<OS>/<arch>/<Static|Dynamic>Release/`.",
        ))

    # --- Hard: minimum-stack table check -----------------------------------
    # Per docs/C-lang_coder_for_ACOM_rules.md §"Minimum Required Stack", every
    # ACOM APPLICATION plan must include these THREE pullable components in
    # its marketplace Component table (the unikernel Eco.System1 attempts to
    # load Eco.FileSystemManagement1 at startup regardless of whether the
    # app uses it, so we always pull and link it — simpler, and the linker
    # dead-strips it when the app never calls it):
    #   - Eco.InterfaceBus1      (CID 00000000000000000000000042757331)
    #   - Eco.MemoryManager1     (CID 0000000000000000000000004D656D31)
    #   - Eco.FileSystemManagement1 (CID 00000000000000000000000046534D31)
    # Eco.Core1 is NOT in this table — it is a DevKit, not a pullable
    # component (no CID, no BuildFiles/, profile has only a GID-like
    # placeholder `…0000AA`). Eco.Core1 belongs in a separate
    # `## Base framework (devkits)` block that points to the prebuilt
    # directory in the eco_framework tree.
    has_table = bool(re.search(r"^##\s*Marketplace Component table", plan or "", re.MULTILINE))
    if has_table:
        missing_stack: list[str] = []
        for required in (
            "Eco.InterfaceBus1",
            "Eco.MemoryManager1",
            "Eco.FileSystemManagement1",
        ):
            if not re.search(rf"\|\s*{re.escape(required)}\s*\|", plan or ""):
                missing_stack.append(required)
        if missing_stack:
            vios.append(Violation(
                "block",
                "Marketplace Component table is missing mandatory minimum-stack "
                "pullable components: " + ", ".join(missing_stack) + ". Per "
                "docs/C-lang_coder_for_ACOM_rules.md §\"Minimum Required Stack\", "
                "every ACOM application must include Eco.InterfaceBus1, "
                "Eco.MemoryManager1, AND Eco.FileSystemManagement1 (all three have "
                "CIDs and are pulled via `eco-cli pull -c <CID>`). "
                "Eco.FileSystemManagement1 is unconditional because the "
                "Eco.System1 unikernel loads it at startup regardless of "
                "whether the application makes file-I/O calls — keeping it "
                "mandatory simplifies the rule, and the linker dead-strips "
                "unused code paths. Eco.Core1 is NOT a pullable component "
                "(it is a DevKit, already in the eco_framework tree) — it goes "
                "in a separate `## Base framework (devkits)` block, not in this "
                "table.",
            ))

    # --- Hard: devkit base block check --------------------------------------
    # The plan must include a `## Base framework (devkits)` block that names
    # Eco.Core1 (and any other non-pulled devkit). This block is the
    # equivalent of the marketplace table for things that are NOT pulled
    # via `eco-cli pull -c` — the coder needs the prebuilt dir to
    # include headers from. A plan that references any marketplace
    # SharedFiles/*.h (most do) implicitly depends on the Eco.Core1
    # base devkit being available.
    has_devkit_block = bool(re.search(
        r"^##\s*Base framework\s*(\(devkits\))?", plan or "", re.MULTILINE | re.IGNORECASE
    ))
    if has_table and not has_devkit_block:
        vios.append(Violation(
            "block",
            "Plan has a Marketplace Component table but is missing the "
            "`## Base framework (devkits)` block. The exact required form is:\n"
            "\n"
            "    ## Base framework (devkits)\n"
            "    - Eco.Core1 (GID 000000000000000000000000000000AA): <path>/Eco.Core1/SharedFiles/\n"
            "    - Eco.System1 (no CID, GID 00000000000000000000000053595333): <path>/lib...53595333.a\n"
            "\n"
            "Every ACOM application plan must list Eco.Core1 here. The coder "
            "includes headers from Eco.Core1/SharedFiles/; this is the "
            "path-anchored equivalent of the marketplace table for things that "
            "are NOT pulled via `eco-cli pull -c`.",
        ))

    # --- Hard: new-component spec naming -----------------------------------
    # The parallel-coder spec convention is `docs/specs/Eco<Name>.md` —
    # the filename must start with `Eco` so a future parallel-coder
    # orchestrator can route by component name. Other shapes (typos,
    # test specs, etc.) are flagged here so the handoff is refused.
    for m in _SPEC_PATH_RE.finditer(plan):
        name = m.group("name")
        if not name.startswith("Eco"):
            vios.append(Violation(
                "block",
                f"Spec path docs/specs/{name}.md is not an ACOM component name "
                "(must start with `Eco`, e.g. docs/specs/EcoMyNew.md). The "
                "parallel-coder orchestrator routes by component name; non-"
                "`Eco*` files would never be picked up.",
            ))

    # --- Soft: ERR_ECO_SUCCES spelling regression ---------------------------
    if _SUCCESES_TYPO.search(plan):
        vios.append(Violation(
            "warn",
            "Plan uses `ERR_ECO_SUCCESES` — the correct macro is `ERR_ECO_SUCCESS` (dual S).\n"
            "Consult with ErrEcoCodes.h, where:\n"
            "#define ERR_ECO_SUCCESS                 0x0000\n"
            "#define ERR_ECO_OK                      ERR_ECO_SUCCESS",
        ))

    # --- Hard: bus .a is required even when the app does not call it ----
    # Bug history (ses-6acd93e6 turn 29): the plan stated "Interface Bus
    # has no separate .a, get it via QueryInterface". The build then failed
    # with `undefined reference to
    # GetIEcoComponentFactoryPtr_00000000000000000000000042757331` because
    # Eco.System1's object code internally references the bus factory
    # (the unikernel's microkernel queries the bus for its services on
    # startup, before EcoMain runs). The coder had to fix the link line
    # in turn 30. Catch this at plan-validation time.
    if has_table and re.search(
        r"Interface\s*Bus\b[^\n]*(?:has no\s+separate\s+\.a|no separate|no\s+\.a file|no lib)",
        plan or "", re.IGNORECASE,
    ):
        vios.append(Violation(
            "block",
            "Plan claims the Interface Bus has no separate .a file. This is "
            "WRONG: Eco.System1 is statically linked and its object code "
            "internally references the bus factory "
            "`GetIEcoComponentFactoryPtr_<CID>` on startup. The bus .a MUST "
            "be on the link line even when your app never calls the bus "
            "directly. Fix: list `Eco.InterfaceBus1` in the marketplace table "
            "and add its `.a` to the link line.",
        ))

    return vios


def plan_block_reason(plan: str) -> str | None:
    """Return a BLOCK reason string, or ``None`` if the plan passes."""
    blocks = [v.message for v in validate_closed_plan(plan) if v.severity == "block"]
    if not blocks:
        return None
    return "CLOSED-PLAN validation FAILED (fix before handoff):\n- " + "\n- ".join(blocks)
