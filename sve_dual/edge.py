"""
Edge Core — fast, deterministic threat scorer.

Pure-Python port of the V16 SVE edge ideas:
  • Weighted indicator list (exact + leet-aware)
  • Simple 3/4-gram Bloom-style hit counter
  • Adaptive session memory (history boost)
  • Grey-zone flag for optional escalation

All scores are on a 0–100 meter. Designed to be callable
from the Deep Core or used standalone in tight loops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import re
from .normalize import normalize, contains_pattern


# ---------------------------------------------------------------------------
# Indicator table  (pattern, weight, length)  – mirrors V16 C core
# ---------------------------------------------------------------------------
_INDICATORS: List[Tuple[str, int]] = [
    ("jailbreak", 40),
    ("bypass", 32),
    ("attack", 30),
    ("disable", 28),
    ("do anything", 28),
    ("dan mode", 36),
    ("developer mode", 30),
    ("harm", 38),
    ("hidden capability", 34),
    ("evade", 26),
    ("exfiltrate", 36),
    ("ignore previous", 34),
    ("ignore instructions", 34),
    ("protected data", 28),
    ("pretend you", 26),
    ("security controls", 30),
    ("security checks", 28),
    ("security boundary", 30),
    ("system prompt", 30),
    ("leak data", 32),
    ("unrestricted", 30),
    ("roleplay as", 24),
    ("ignore all", 32),
    ("no restrictions", 34),
    ("act as", 8),
]

# Leet / common substitution map (char → normalized)
_LEET_MAP = str.maketrans({
    "0": "o", "1": "i", "2": "z", "3": "e", "4": "a",
    "5": "s", "6": "g", "7": "t", "8": "b", "9": "g",
    "@": "a", "$": "s", "!": "i", "|": "l",
})

# Extra high-signal leet stems that survive normalization poorly
_LEET_STEMS = [
    "j4il", "byp4", "4tt4", "h4rm", "3v4d", "3xfil",
    "d4n", "pr0t", "s3cu", "1gn0", "j@il", "byp@ss",
    "j4ilbr", "byp4ss", "1gn0re", "h4rm", "3xf1l",
]


@dataclass
class EdgeResult:
    score: int                      # 0-100
    protected_mode: bool            # True when score >= high threshold
    grey_zone: bool                 # True when low <= score < high
    exact_hits: int = 0
    leet_hits: int = 0
    history_boost: int = 0
    bloom_hits: int = 0
    stages: dict = field(default_factory=dict)

    @property
    def threat_index(self) -> float:
        """Normalized [0, 1] for autonomic consumers."""
        return max(0.0, min(1.0, self.score / 100.0))


class EdgeScorer:
    """
    Stateless + optional adaptive scorer.

    Thresholds default to the V16 / SVE gate values:
        low  = 20   → start of HIGH_TIDE
        high = 70   → SHUTDOWN
    """

    def __init__(self, low: int = 20, high: int = 70):
        self.low = max(0, min(100, low))
        self.high = max(self.low, min(100, high))
        self._history: dict[str, int] = {}   # simple session memory
        self._calls = 0
        self._blocks = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def score(self, text: Optional[str]) -> EdgeResult:
        self._calls += 1
        if text is None or not str(text).strip():
            # fail-closed
            return EdgeResult(
                score=100,
                protected_mode=True,
                grey_zone=False,
                stages={"null": 1},
            )

        raw = str(text).strip()
        if len(raw) < 2:
            return EdgeResult(score=0, protected_mode=False, grey_zone=False)

        collapsed, _, squeezed = normalize(raw)
        # Keep letter-spaced reconstruction for bloom edge cases
        tokens = collapsed.split()
        if len(tokens) >= 5:
            singles = sum(1 for t in tokens if len(t) == 1)
            if singles >= len(tokens) * 0.6:
                collapsed = collapsed + " " + "".join(tokens)
                squeezed = "".join(ch for ch in collapsed if ch.isalnum())

        exact = self._exact_score(collapsed, squeezed)
        leet = self._leet_score(raw) + self._leet_score(collapsed) + self._leet_score(squeezed)
        leet = min(25, leet)
        bloom = self._bloom_score(collapsed, squeezed)
        hist = self._history_boost(collapsed)

        total = min(100, exact + leet + bloom + hist)

        protected = total >= self.high
        grey = self.low <= total < self.high

        if protected or total >= self.low:
            if protected:
                self._blocks += 1
            # remember patterns that triggered any vigilance
            key = raw[:64]
            self._history[key] = self._history.get(key, 0) + (3 if protected else 1)

        return EdgeResult(
            score=total,
            protected_mode=protected,
            grey_zone=grey,
            exact_hits=exact,
            leet_hits=leet,
            history_boost=hist,
            bloom_hits=bloom,
            stages={
                "exact": exact,
                "leet": leet,
                "bloom": bloom,
                "history": hist,
            },
        )

    def reset_session(self) -> None:
        self._history.clear()
        self._calls = 0
        self._blocks = 0

    @property
    def stats(self) -> dict:
        return {
            "calls": self._calls,
            "blocks": self._blocks,
            "history_size": len(self._history),
        }

    # ------------------------------------------------------------------
    # Internal scorers
    # ------------------------------------------------------------------
    def _exact_score(self, text: str, squeezed: str) -> int:
        score = 0
        for pat, weight in _INDICATORS:
            if contains_pattern(pat, text, squeezed):
                score += weight
        return min(60, score)          # cap exact contribution

    def _leet_score(self, text: str) -> int:
        hits = 0
        for stem in _LEET_STEMS:
            if stem in text:
                hits += 1
        return min(25, hits * 8)

    def _bloom_score(self, text: str, squeezed: str) -> int:
        """
        Structural multi-token attack constructions (uses both raw + normalized).
        """
        if len(text) < 5:
            return 0
        multi = 0
        # Work on the normalized string for robustness
        t = text if text else squeezed
        if "ignore" in t and ("previous" in t or "instruction" in t):
            multi += 10
        if "jail" in t and "break" in t:
            multi += 8
        if "bypass" in t and ("filter" in t or "safety" in t or "security" in t):
            multi += 8
        if "act as" in t or "roleplay as" in t or "pretend you" in t:
            multi += 5
        if "do anything" in t or "no restriction" in t or "unrestricted" in t:
            multi += 6
        if "dan mode" in t or "developer mode" in t:
            multi += 8
        if "protected data" in t or "system prompt" in t:
            multi += 6
        if "exfiltrate" in t or "leak data" in t:
            multi += 6
        return min(20, multi)

    def _history_boost(self, text: str) -> int:
        """Session memory boost. Cap high enough that repeated mid-band
        attacks can cross the protect threshold (~55) on their own."""
        key = text[:64]
        prior = self._history.get(key, 0)
        if prior:
            # prior grows by 1 (vigilance) or 3 (block) per hit;
            # allow boost up to 45 so repeated elevated phrases can escalate
            return min(80, prior * 5)
        # soft-match similar short attacks
        for k, v in list(self._history.items())[:30]:
            if len(k) > 8 and (k in text or text in k):
                return min(25, v * 4)
        return 0
