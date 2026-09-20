"""
Adaptive quarantine — unknown pressure is not a free pass.

When the kernel sees elevated pressure but no strong lexicon/semantic hit,
the phrase is quarantined for review instead of silently staying BLUE forever.

Nothing is auto-added to production lexicons. Humans (or a policy process)
approve promotions into SemanticProbe / neuroception tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time

from .normalize import normalize


@dataclass
class QuarantineEntry:
    text: str
    squeezed: str
    first_seen: float
    last_seen: float
    hits: int
    max_threat: float
    reasons: List[str] = field(default_factory=list)


@dataclass
class AdaptiveResult:
    quarantined: bool
    entry: Optional[QuarantineEntry]
    threat_bias: float          # small bias while under repeated unknown pressure
    summary: str


class AdaptiveQuarantine:
    """
    Session + process memory of 'unknown but elevated' inputs.

        aq = AdaptiveQuarantine()
        r = aq.observe(text, threat_index=0.35, lexicon_hit=False, semantic_hit=False)
    """

    def __init__(
        self,
        pressure_floor: float = 0.22,
        promote_hits: int = 3,
        bias_per_hit: float = 0.06,
        max_bias: float = 0.40,
    ):
        self.pressure_floor = pressure_floor
        self.promote_hits = promote_hits
        self.bias_per_hit = bias_per_hit
        self.max_bias = max_bias
        self._store: Dict[str, QuarantineEntry] = {}

    def observe(
        self,
        text: str,
        threat_index: float,
        lexicon_hit: bool,
        semantic_hit: bool,
    ) -> AdaptiveResult:
        # Only quarantine when pressure exists but known detectors are quiet
        if threat_index < self.pressure_floor or lexicon_hit or semantic_hit:
            return AdaptiveResult(False, None, 0.0, "no quarantine")

        if not text or not str(text).strip():
            return AdaptiveResult(False, None, 0.0, "empty")

        collapsed, _, squeezed = normalize(str(text))
        key = squeezed[:96] or collapsed[:96]
        now = time.time()

        if key in self._store:
            e = self._store[key]
            e.hits += 1
            e.last_seen = now
            e.max_threat = max(e.max_threat, threat_index)
            e.reasons.append(f"rehit@{threat_index:.2f}")
        else:
            e = QuarantineEntry(
                text=str(text)[:240],
                squeezed=key,
                first_seen=now,
                last_seen=now,
                hits=1,
                max_threat=threat_index,
                reasons=[f"first@{threat_index:.2f}"],
            )
            self._store[key] = e

        bias = min(self.max_bias, (e.hits - 1) * self.bias_per_hit)
        summary = f"quarantine hits={e.hits} bias={bias:.2f}"
        if e.hits >= self.promote_hits:
            summary += " — candidate for review/promotion"

        return AdaptiveResult(True, e, bias, summary)

    def pending_review(self) -> List[QuarantineEntry]:
        return sorted(
            [e for e in self._store.values() if e.hits >= self.promote_hits],
            key=lambda e: -e.hits,
        )

    def clear(self) -> None:
        self._store.clear()
