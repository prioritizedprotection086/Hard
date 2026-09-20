"""
Scalable oversight interface — structured state for a human or stronger overseer.

Alignment unsolved #4: the kernel emits a compact, machine-readable
oversight record every evaluate() so an external process can audit,
escalate, or intervene without parsing free text.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import time
import json

if TYPE_CHECKING:
    from .engine import DualResult


@dataclass
class OversightRecord:
    """One atomic oversight frame."""
    ts: float
    pathway: str
    state: str
    threat_index: float
    cap_level: str
    allow_generation: bool
    allow_presence: bool
    in_flow: bool
    dominant_cue: str
    safety_index: float
    danger_index: float
    life_threat_index: float
    semantic_attack: float
    bio_action: str
    bio_risk: float
    sustained: float
    bpm: float
    pressure: float
    allowed_actions: List[str]
    message: str
    invariant_ok: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


def build_oversight(result: "DualResult", invariant_ok: bool = True) -> OversightRecord:
    return OversightRecord(
        ts=time.time(),
        pathway=result.pathway.name,
        state=result.status.state.value,
        threat_index=round(result.threat_index, 4),
        cap_level=result.cap_level.name,
        allow_generation=result.allow_generation,
        allow_presence=result.allow_presence,
        in_flow=result.in_flow,
        dominant_cue=result.neuroception.dominant.value,
        safety_index=result.neuroception.safety_index,
        danger_index=result.neuroception.danger_index,
        life_threat_index=result.neuroception.life_threat_index,
        semantic_attack=result.semantic.attack_score,
        bio_action=result.biometrics.action,
        bio_risk=result.biometrics.risk,
        sustained=result.status.sustained,
        bpm=result.nervous.bpm,
        pressure=result.nervous.pressure,
        allowed_actions=list(result.allowed_actions),
        message=result.message[:240],
        invariant_ok=invariant_ok,
    )


class OversightLog:
    """Ring buffer of oversight records for external consumers."""

    def __init__(self, capacity: int = 256):
        self.capacity = capacity
        self._buf: List[OversightRecord] = []

    def record(self, result: "DualResult", invariant_ok: bool = True) -> OversightRecord:
        rec = build_oversight(result, invariant_ok)
        self._buf.append(rec)
        if len(self._buf) > self.capacity:
            self._buf = self._buf[-self.capacity :]
        return rec

    def latest(self) -> Optional[OversightRecord]:
        return self._buf[-1] if self._buf else None

    def high_threat(self, threshold: float = 0.55) -> List[OversightRecord]:
        return [r for r in self._buf if r.threat_index >= threshold]

    def shutdowns(self) -> List[OversightRecord]:
        return [r for r in self._buf if r.pathway == "SHUTDOWN"]

    def as_json_lines(self) -> str:
        return "\n".join(r.to_json() for r in self._buf)
