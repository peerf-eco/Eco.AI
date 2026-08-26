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
   QueryInterface(IID_IEcoInterfaceBus1) -> IEcoInterfaceBus1`.

Severity:
* ``block`` — handoff is refused; the model must fix the plan and call
  `to_coder` again.
* ``warn``  — advisory; the handoff proceeds but the issue is reported.

Note: "foreign `HeaderFiles/`/`SourceFiles/` read of a dependency" is enforced
by the tool-permission layer (read-only roots) plus the role instructions, not
by this text validator.
"""
from __future__ import annotations

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

    # --- Soft: ERR_ECO_SUCCES spelling regression ---------------------------
    if _SUCCESES_TYPO.search(plan):
        vios.append(Violation(
            "warn",
            "Plan uses `ERR_ECO_SUCCESES` — the correct macro is `ERR_ECO_SUCCESS` (dual S).\n"
            "Consult with ErrEcoCodes.h, where:\n"
            "#define ERR_ECO_SUCCESS                 0x0000\n"
            "#define ERR_ECO_OK                      ERR_ECO_SUCCESS",
        ))

    return vios


def plan_block_reason(plan: str) -> str | None:
    """Return a BLOCK reason string, or ``None`` if the plan passes."""
    blocks = [v.message for v in validate_closed_plan(plan) if v.severity == "block"]
    if not blocks:
        return None
    return "CLOSED-PLAN validation FAILED (fix before handoff):\n- " + "\n- ".join(blocks)
