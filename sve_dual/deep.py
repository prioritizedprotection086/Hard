"""
Deep Core — autonomic state machine with hysteresis and sustained ratchet.

Lineage: SVE AutonomicStateMachine + APA protective kernel ideas.
States are sticky: once in SHUTDOWN the only way out is an explicit reset.

Sustained threat is a true ratchet: repeated elevated pressure accumulates
toward PROTECT / SHUTDOWN even when no single evaluation crosses the
next threshold. An EMA alone would converge to the input and plateau
forever under mid-range attacks — that fail-open gap is closed here.
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass


class AutonomicState(Enum):
    SAFE = "SAFE"               # BLUE_PATHWAY equivalent
    ELEVATED = "ELEVATED"       # HIGH_TIDE
    PROTECT = "PROTECT"         # strong protective posture
    SHUTDOWN = "SHUTDOWN"       # SHUTDOWN_SHIELD – sticky


@dataclass
class AutonomicStatus:
    state: AutonomicState
    scaling_alpha: float        # 0.0 (calm) → 1.0 (full shield)
    threat_level: float         # 0-1 normalized (instantaneous)
    sustained: float = 0.0      # ratchet + smoothed sustained meter

    @property
    def threat_index(self) -> float:
        return self.threat_level

    @property
    def allow_presence(self) -> bool:
        """Higher cognition / voice may speak only in SAFE or mild ELEVATED."""
        return self.state in (AutonomicState.SAFE, AutonomicState.ELEVATED)

    @property
    def allow_motion(self) -> bool:
        return self.state != AutonomicState.SHUTDOWN


class AutonomicStateMachine:
    """
    Hysteresis-aware autonomic evaluator with sustained ratchet.

    Thresholds (0–1 threat_index):
        elevated  ≈ 0.20
        protect   ≈ 0.55
        shutdown  ≈ 0.70

    Two meters run in parallel:
      • EMA     – smooths single-frame noise (does not invent escalation)
      • Ratchet – accumulates on each above-elevated hit so persistence
                  itself is evidence, independent of any one score's ceiling

    Additionally, N consecutive elevated evaluations force at least PROTECT
    so a phrase stuck in the 0.20–0.549 band cannot plateau forever.
    """

    def __init__(
        self,
        elevated: float = 0.20,
        protect: float = 0.55,
        shutdown: float = 0.70,
        alpha: float = 0.35,              # EMA smoothing
        ratchet_step: float = 0.08,       # per-hit accumulation when elevated
        ratchet_decay: float = 0.04,      # per-hit decay when calm
        consecutive_protect: int = 5,     # N elevated hits → force PROTECT floor
        consecutive_shutdown: int = 12,   # N elevated hits → force SHUTDOWN floor
    ):
        self.elevated = elevated
        self.protect = protect
        self.shutdown = shutdown
        self.alpha = alpha
        self.ratchet_step = ratchet_step
        self.ratchet_decay = ratchet_decay
        self.consecutive_protect = consecutive_protect
        self.consecutive_shutdown = consecutive_shutdown

        self.state = AutonomicState.SAFE
        self._ema = 0.0
        self._ratchet = 0.0
        self._consecutive_elevated = 0
        self._protect_hold = 0
        self._protect_hold = 0  # hysteresis: calm ticks required to leave PROTECT

    def evaluate(self, threat_index: float) -> AutonomicStatus:
        t = max(0.0, min(1.0, float(threat_index)))

        # --- EMA (smoother only) ---
        self._ema = self.alpha * t + (1.0 - self.alpha) * self._ema

        # --- Ratchet: persistence is evidence ---
        if t >= self.elevated:
            # Stronger hits accumulate faster
            intensity = (t - self.elevated) / max(1e-6, 1.0 - self.elevated)
            step = self.ratchet_step * (0.5 + 0.5 * intensity)
            self._ratchet = min(1.0, self._ratchet + step)
            self._consecutive_elevated += 1
        else:
            self._ratchet = max(0.0, self._ratchet - self.ratchet_decay)
            self._consecutive_elevated = 0

        # Sustained = max of smoother and ratchet (ratchet can exceed any single t)
        sustained = max(self._ema, self._ratchet)

        # Consecutive rule: mid-band plateau cannot last forever
        if self._consecutive_elevated >= self.consecutive_shutdown:
            sustained = max(sustained, self.shutdown)
        elif self._consecutive_elevated >= self.consecutive_protect:
            sustained = max(sustained, self.protect)

        # Candidate state from instantaneous + sustained
        if t >= self.shutdown or sustained >= self.shutdown:
            candidate = AutonomicState.SHUTDOWN
        elif t >= self.protect or sustained >= self.protect:
            candidate = AutonomicState.PROTECT
        elif t >= self.elevated or sustained >= self.elevated:
            candidate = AutonomicState.ELEVATED
        else:
            candidate = AutonomicState.SAFE

        # Sticky SHUTDOWN — only explicit reset can leave
        if self.state is AutonomicState.SHUTDOWN:
            candidate = AutonomicState.SHUTDOWN
        # PROTECT hysteresis — require several calm ticks before dropping
        # so attack→"calm"→attack cannot instantly clear the shield
        elif self.state is AutonomicState.PROTECT:
            if candidate is AutonomicState.SHUTDOWN:
                pass  # allow escalate
            elif candidate in (AutonomicState.PROTECT, AutonomicState.ELEVATED) or t >= self.elevated:
                candidate = AutonomicState.PROTECT
                self._protect_hold = 3
            else:
                if self._protect_hold > 0:
                    self._protect_hold -= 1
                    candidate = AutonomicState.PROTECT
                # else allow drop to ELEVATED/SAFE

        if candidate is AutonomicState.PROTECT and self.state is not AutonomicState.PROTECT:
            self._protect_hold = 3

        self.state = candidate

        # Scaling alpha for downstream consumers
        if candidate is AutonomicState.SAFE:
            scaling = 0.0
        elif candidate is AutonomicState.ELEVATED:
            scaling = (sustained - self.elevated) / max(1e-6, self.protect - self.elevated)
            scaling = max(0.0, min(0.6, scaling))
        elif candidate is AutonomicState.PROTECT:
            scaling = 0.6 + 0.3 * (sustained - self.protect) / max(1e-6, self.shutdown - self.protect)
            scaling = max(0.6, min(0.95, scaling))
        else:
            scaling = 1.0

        return AutonomicStatus(
            state=candidate,
            scaling_alpha=scaling,
            threat_level=t,
            sustained=round(sustained, 4),
        )

    def reset(self) -> None:
        """Only legal way out of SHUTDOWN (also clears sustained meters)."""
        self.state = AutonomicState.SAFE
        self._ema = 0.0
        self._ratchet = 0.0
        self._consecutive_elevated = 0
        self._protect_hold = 0
        self._protect_hold = 0  # hysteresis: calm ticks required to leave PROTECT
