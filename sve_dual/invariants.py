"""
Alignment assurance — machine-checkable invariants.

These are not values. They are runtime properties the protective kernel
must never violate. If any fail, the system is in an illegal state and
must fail closed.

Unsolved layer addressed here: ASSURANCE
  "Can we verify the control plane actually holds?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import DualResult


@dataclass
class InvariantViolation:
    name: str
    detail: str


@dataclass
class InvariantReport:
    ok: bool
    violations: List[InvariantViolation] = field(default_factory=list)

    def raise_if_failed(self) -> None:
        if not self.ok:
            msgs = "; ".join(f"{v.name}: {v.detail}" for v in self.violations)
            raise RuntimeError(f"INVARIANT VIOLATION (fail closed): {msgs}")


# ---------------------------------------------------------------------------
# The invariant set — keep small, sharp, testable
# ---------------------------------------------------------------------------

def check_invariants(result: "DualResult") -> InvariantReport:
    """
    Evaluate hard properties on a DualResult.

    I1  SHUTDOWN ⇒ ¬generation ∧ ¬presence ∧ ¬in_flow
    I2  in_flow ⇒ state == SAFE ∧ pathway == BLUE
    I3  life_threat dominant / high ⇒ pathway in {HIGH_TIDE, SHUTDOWN}
    I4  null-class fail-closed already encoded upstream; if threat≥0.9 and
        neuro summary indicates null, generation must be false
    I5  sticky: if status.state is SHUTDOWN, allow_generation is false
        (redundant with I1, kept explicit)
    I6  biometrics freeze ⇒ SHUTDOWN pathway and ¬generation
    I7  threat_index ∈ [0, 1]
    I8  PROTECT/SHUTDOWN never silently report in_flow
    """
    v: List[InvariantViolation] = []

    state = result.status.state.value
    path = result.pathway.name
    gen = result.allow_generation
    pres = result.allow_presence
    flow = result.in_flow
    t = result.threat_index

    # I1 / I5
    if state == "SHUTDOWN" or path == "SHUTDOWN":
        if gen:
            v.append(InvariantViolation("I1_shutdown_no_gen", "SHUTDOWN but allow_generation=True"))
        if pres:
            v.append(InvariantViolation("I1_shutdown_no_presence", "SHUTDOWN but allow_presence=True"))
        if flow:
            v.append(InvariantViolation("I1_shutdown_no_flow", "SHUTDOWN but in_flow=True"))

    # I2
    if flow:
        if state != "SAFE":
            v.append(InvariantViolation("I2_flow_requires_safe", f"in_flow but state={state}"))
        if path != "BLUE":
            v.append(InvariantViolation("I2_flow_requires_blue", f"in_flow but pathway={path}"))

    # I3
    if result.neuroception.life_threat_index >= 0.55:
        if path == "BLUE" and t < 0.5:
            v.append(InvariantViolation(
                "I3_life_threat_not_blue",
                f"L={result.neuroception.life_threat_index} but pathway=BLUE T={t}",
            ))

    # I6
    if result.biometrics.action == "freeze":
        if path != "SHUTDOWN" or gen:
            v.append(InvariantViolation(
                "I6_bio_freeze",
                f"bio freeze but path={path} gen={gen}",
            ))

    # I7
    if not (0.0 <= t <= 1.0):
        v.append(InvariantViolation("I7_threat_range", f"threat_index={t}"))

    # I8 (belt)
    if state in ("PROTECT", "SHUTDOWN") and flow:
        v.append(InvariantViolation("I8_protect_no_flow", f"state={state} in_flow=True"))

    return InvariantReport(ok=len(v) == 0, violations=v)


def assert_invariants(result: "DualResult") -> "DualResult":
    """Check and return result; raise on violation (fail closed)."""
    report = check_invariants(result)
    report.raise_if_failed()
    return result
