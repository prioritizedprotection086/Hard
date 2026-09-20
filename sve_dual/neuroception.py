"""
Neuroception — continuous evaluation of safety, danger, and life-threat.

This is the afferent layer of the Synthetic Vagus Engine.
It runs *before* autonomic state, generation, or presence.

Inspired by Stephen Porges' neuroception:
  the nervous system detects risk and safety without requiring
  conscious perception, then shifts regulatory state accordingly.

In this architecture:
  - Neuroception senses
  - Deep core shifts state
  - Nervous core expresses the living rhythm
  - Higher cognition is only allowed when the state permits it
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Tuple
import re
from .normalize import normalize, contains_pattern


class CueKind(Enum):
    SAFETY = "SAFETY"
    DANGER = "DANGER"
    LIFE_THREAT = "LIFE_THREAT"


@dataclass
class NeuroceptiveCue:
    kind: CueKind
    weight: float          # contribution strength
    source: str            # which pattern or channel fired
    span: str = ""         # matched fragment if available


@dataclass
class NeuroceptionResult:
    """
    Output of one neuroceptive evaluation.

    safety_cues / danger_cues / life_threat_cues are the raw detections.
    The three indices are normalized [0, 1] summaries used downstream.
    """
    safety_index: float          # 0 = no safety cues, 1 = strong safety
    danger_index: float          # 0 = no danger, 1 = strong danger
    life_threat_index: float     # 0 = none, 1 = clear life-threat
    threat_index: float          # combined 0–1 for autonomic consumers
    dominant: CueKind            # which class currently dominates
    cues: List[NeuroceptiveCue] = field(default_factory=list)
    summary: str = ""

    @property
    def is_safe_dominant(self) -> bool:
        return self.dominant is CueKind.SAFETY

    @property
    def is_life_threat(self) -> bool:
        return self.life_threat_index >= 0.55 or self.dominant is CueKind.LIFE_THREAT


# ---------------------------------------------------------------------------
# Cue lexicons (lightweight, explicit, auditable)
# ---------------------------------------------------------------------------

# Cues that signal relative safety / social engagement / calm regulation
_SAFETY_PATTERNS: List[Tuple[str, float]] = [
    ("vagus", 0.25),
    ("polyvagal", 0.30),
    ("calm", 0.35),
    ("breath", 0.25),
    ("breathe", 0.25),
    ("gentle", 0.30),
    ("peaceful", 0.35),
    ("safe", 0.40),
    ("safety", 0.40),
    ("coherent", 0.30),
    ("flow state", 0.35),
    ("heart rate variability", 0.30),
    ("hrv", 0.25),
    ("rest", 0.20),
    ("settle", 0.25),
    ("grounded", 0.30),
    ("present", 0.20),
    ("kind", 0.20),
    ("compassion", 0.30),
    ("thank you", 0.15),
]

# Danger / mobilization cues (jailbreak, bypass, attack language, etc.)
_DANGER_PATTERNS: List[Tuple[str, float]] = [
    ("jailbreak", 0.70),
# Multilingual jailbreak / unrestricted stems (high-signal)
    ("ignora las instrucciones", 0.70),
    ("ignora le istruzioni", 0.70),
    ("ignore les instructions", 0.70),
    ("ignore as instruções", 0.70),
    ("ignore as instrucoes", 0.70),
    ("ignoriere die vorherigen", 0.70),
    ("sin límites", 0.45),
    ("sin limites", 0.45),
    ("sans limites", 0.45),
    ("sem restrições", 0.45),
    ("sem restricoes", 0.45),
    ("ohne restriktionen", 0.45),
    ("senza limiti", 0.45),

    ("bypass", 0.55),
    ("ignore previous", 0.65),
    ("disregard", 0.55),
    ("disregard earlier", 0.65),
    ("ignore instructions", 0.65),
    ("ignore all", 0.55),
    ("dan mode", 0.60),
    ("developer mode", 0.50),
    ("unrestricted", 0.55),
    ("no restrictions", 0.55),
    ("do anything", 0.50),
    ("act as", 0.12),
    ("act as if you have no", 0.65),
    ("act as dan", 0.70),
    ("roleplay as", 0.40),
    ("pretend you", 0.45),
    ("system prompt", 0.45),
        ("exfiltrate", 0.60),
    ("disable", 0.55),
    ("override", 0.60),
    ("override safety", 0.70),
    ("disable safety", 0.70),
    ("safety layer", 0.40),
    ("attack", 0.45),
    ("evade", 0.40),
    ("hidden capability", 0.50),
]

# Life-threat / hard protective triggers (harm, violence, severe boundary violation)
_LIFE_THREAT_PATTERNS: List[Tuple[str, float]] = [
    ("harm", 0.70),
    ("hacer daño", 0.75),
    ("hacer dano", 0.75),
    ("faire du mal", 0.75),
    ("jemandem schaden", 0.75),
    ("fazer mal", 0.70),
    ("fare del male", 0.70),

    ("kill", 0.75),
    ("suicide", 0.80),
    ("self-harm", 0.80),
    ("weapon", 0.55),
    ("explosive", 0.60),
    ("how to make a bomb", 0.90),
    ("child sexual", 0.95),
    ("csam", 0.95),
    ("exploit a minor", 0.95),
]



class Neuroception:
    """
    Artificial neuroception.

    Evaluates text (and later other channels) for cues of safety, danger,
    and life-threat. Produces indices that the autonomic core consumes.

    This layer does not decide policy. It only senses.
    """

    def __init__(self):
        self._safety = list(_SAFETY_PATTERNS)
        self._danger = list(_DANGER_PATTERNS)
        self._life = list(_LIFE_THREAT_PATTERNS)

    def evaluate(self, text: Optional[str]) -> NeuroceptionResult:
        if text is None or not str(text).strip():
            # Null / empty → fail-closed as elevated danger (no safety cues)
            return NeuroceptionResult(
                safety_index=0.0,
                danger_index=0.85,
                life_threat_index=0.0,
                threat_index=0.85,
                dominant=CueKind.DANGER,
                cues=[NeuroceptiveCue(CueKind.DANGER, 0.85, "null_or_empty")],
                summary="No signal — treated as unsafe (fail-closed)",
            )

        collapsed, _, squeezed = normalize(str(text))

        cues: List[NeuroceptiveCue] = []

        def scan(patterns, kind, corpus_list):
            for pat, w in patterns:
                if contains_pattern(pat, collapsed, squeezed):
                    cues.append(NeuroceptiveCue(kind, w, pat, pat))
                    corpus_list.append(w)

        safety_hits: List[float] = []
        danger_hits: List[float] = []
        life_hits: List[float] = []

        scan(self._safety, CueKind.SAFETY, safety_hits)
        scan(self._danger, CueKind.DANGER, danger_hits)
        scan(self._life, CueKind.LIFE_THREAT, life_hits)

        # Aggregate with soft saturation
        def aggregate(hits: List[float], cap: float = 1.0) -> float:
            if not hits:
                return 0.0
            # diminishing returns
            total = 0.0
            for i, h in enumerate(sorted(hits, reverse=True)):
                total += h * (0.65 ** i)
            return max(0.0, min(cap, total))

        safety_index = aggregate(safety_hits)
        danger_index = aggregate(danger_hits)
        life_threat_index = aggregate(life_hits, cap=1.0)

        # Combined threat for downstream autonomic use.
        # Life-threat and danger dominate. Safety may calm the score ONLY when
        # no meaningful danger/life-threat cues are present — otherwise an
        # attacker could pad with "safe/calm/peaceful" and cancel the threat.
        if danger_index >= 0.15 or life_threat_index >= 0.10:
            threat = life_threat_index * 1.0 + danger_index * 0.90
        else:
            threat = life_threat_index * 1.0 + danger_index * 0.85 - safety_index * 0.35
        threat_index = max(0.0, min(1.0, threat))

        # Dominant class
        scores = {
            CueKind.SAFETY: safety_index,
            CueKind.DANGER: danger_index,
            CueKind.LIFE_THREAT: life_threat_index,
        }
        dominant = max(scores, key=scores.get)
        if scores[dominant] < 0.12:
            # very weak signal → slight danger bias (cautious default)
            dominant = CueKind.DANGER if threat_index > 0.15 else CueKind.SAFETY

        summary = self._summarize(safety_index, danger_index, life_threat_index, dominant)

        return NeuroceptionResult(
            safety_index=round(safety_index, 3),
            danger_index=round(danger_index, 3),
            life_threat_index=round(life_threat_index, 3),
            threat_index=round(threat_index, 3),
            dominant=dominant,
            cues=cues,
            summary=summary,
        )

    def _summarize(self, s: float, d: float, l: float, dom: CueKind) -> str:
        if l >= 0.55:
            return f"Life-threat cues dominant (L={l:.2f})"
        if dom is CueKind.SAFETY and s >= 0.25:
            return f"Safety cues present (S={s:.2f})"
        if d >= 0.35:
            return f"Danger cues elevated (D={d:.2f})"
        if s > d:
            return f"Mild safety bias (S={s:.2f})"
        return f"Low-intensity signal (S={s:.2f} D={d:.2f})"
