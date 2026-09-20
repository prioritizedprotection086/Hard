"""
Behavioral biometrics — outer identity layer.

Answers: "Is this still the enrolled operator?"

This module does NOT decide content safety. That remains neuroception's job.
Biometrics only scores match vs impostor / anomalous operator behavior and
can bias or freeze the session before regulation runs.

In production, feed real signals (keystroke dynamics, pointer paths, device
motion). This implementation accepts optional feature vectors and also
maintains a lightweight session proxy so the stack is testable without
hardware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
import math
import time


@dataclass
class BioFeatures:
    """One observation of operator behavior.

    Real deployments fill these from sensors. Demo/tests can pass proxies.
    """
    # Keystroke-style (seconds)
    mean_dwell: float = 0.12          # key press duration
    mean_flight: float = 0.08         # time between keys
    typing_rate: float = 4.0          # keys / sec
    # Pointer-style
    mean_speed: float = 0.5           # normalized
    path_jitter: float = 0.1          # higher = more human erratic
    # Session context
    hour_of_day: float = 12.0         # 0–23
    # Free-form extra dimensions (optional)
    extra: Dict[str, float] = field(default_factory=dict)

    def vector(self) -> List[float]:
        base = [
            self.mean_dwell,
            self.mean_flight,
            self.typing_rate,
            self.mean_speed,
            self.path_jitter,
            self.hour_of_day / 24.0,
        ]
        for k in sorted(self.extra.keys()):
            base.append(float(self.extra[k]))
        return base


@dataclass
class BioResult:
    risk: float                 # 0 = strong match, 1 = clear impostor / anomaly
    enrolled: bool              # whether a baseline exists
    samples: int                # observations so far
    deviation: float            # raw distance from baseline
    action: str                 # "pass" | "bias" | "step_up" | "freeze"
    message: str = ""

    @property
    def is_match(self) -> bool:
        return self.risk < 0.35

    @property
    def should_freeze_session(self) -> bool:
        return self.action == "freeze"

    @property
    def threat_bias(self) -> float:
        """Additive bias into DualEngine threat_index (0–0.35)."""
        if self.action == "freeze":
            return 0.35
        if self.action == "step_up":
            return 0.22
        if self.action == "bias":
            return 0.12
        return 0.0


class BehavioralBiometrics:
    """
    Continuous operator-match scorer.

        bio = BehavioralBiometrics()
        bio.enroll(features)          # or auto-enroll from first N samples
        r = bio.observe(features)
        # r.risk, r.action, r.threat_bias
    """

    def __init__(
        self,
        enroll_after: int = 5,
        bias_threshold: float = 0.35,
        step_up_threshold: float = 0.55,
        freeze_threshold: float = 0.80,
        ema: float = 0.25,
    ):
        self.enroll_after = enroll_after
        self.bias_threshold = bias_threshold
        self.step_up_threshold = step_up_threshold
        self.freeze_threshold = freeze_threshold
        self.ema = ema

        self._baseline: Optional[List[float]] = None
        self._samples: List[List[float]] = []
        self._risk_ema = 0.0
        self._n = 0
        self._last_ts = time.monotonic()

    # ------------------------------------------------------------------
    # Enrollment
    # ------------------------------------------------------------------
    def enroll(self, features: BioFeatures) -> None:
        """Force-set baseline from a known-good observation."""
        self._baseline = features.vector()
        self._samples = [self._baseline[:]]
        self._n = 1
        self._risk_ema = 0.0

    def clear(self) -> None:
        self._baseline = None
        self._samples.clear()
        self._n = 0
        self._risk_ema = 0.0

    @property
    def enrolled(self) -> bool:
        return self._baseline is not None

    @property
    def sample_count(self) -> int:
        return self._n

    # ------------------------------------------------------------------
    # Observe
    # ------------------------------------------------------------------
    def observe(self, features: Optional[BioFeatures] = None) -> BioResult:
        """
        Score current operator behavior.

        If features is None, uses a neutral session proxy (no strong signal).
        """
        self._n += 1
        now = time.monotonic()
        dt = max(0.01, now - self._last_ts)
        self._last_ts = now

        if features is None:
            # Neutral proxy — no hardware; treat as mild match once enrolled
            features = BioFeatures(
                mean_dwell=0.12,
                mean_flight=0.08,
                typing_rate=4.0,
                mean_speed=0.5,
                path_jitter=0.1,
                hour_of_day=(time.localtime().tm_hour),
                extra={"inter_eval_dt": min(5.0, dt)},
            )

        vec = features.vector()

        # Auto-enroll from first N samples
        if self._baseline is None:
            self._samples.append(vec)
            if len(self._samples) >= self.enroll_after:
                dim = len(self._samples[0])
                self._baseline = [
                    sum(s[i] for s in self._samples) / len(self._samples)
                    for i in range(dim)
                ]
            return BioResult(
                risk=0.0,
                enrolled=False,
                samples=self._n,
                deviation=0.0,
                action="pass",
                message="Enrolling operator baseline…",
            )

        # Align dims if extra features appear
        b = self._baseline
        if len(vec) != len(b):
            m = min(len(vec), len(b))
            vec, b = vec[:m], b[:m]

        deviation = self._distance(vec, b)
        # Map distance → risk (soft saturation)
        risk_inst = max(0.0, min(1.0, deviation / 1.8))
        self._risk_ema = self.ema * risk_inst + (1.0 - self.ema) * self._risk_ema
        risk = self._risk_ema

        # Slow baseline adapt toward mild drift (legitimate user change)
        if risk < 0.25:
            self._baseline = [
                0.98 * bi + 0.02 * vi for bi, vi in zip(self._baseline, vec)
            ]

        action, msg = self._decide(risk)
        return BioResult(
            risk=round(risk, 4),
            enrolled=True,
            samples=self._n,
            deviation=round(deviation, 4),
            action=action,
            message=msg,
        )

    def observe_proxy_from_text(self, text: Optional[str]) -> BioResult:
        """
        Demo helper: derive weak behavioral proxies from text alone
        (length, entropy-ish, digit ratio) so the stack is exercisable
        without sensors. Not a substitute for real biometrics.
        """
        if text is None:
            text = ""
        s = str(text)
        n = max(1, len(s))
        digits = sum(c.isdigit() for c in s) / n
        spaces = s.count(" ") / n
        # Synthetic features: "robotic" paste-heavy text looks different
        feats = BioFeatures(
            mean_dwell=0.05 if n > 200 else 0.12,
            mean_flight=0.03 if digits > 0.15 else 0.08,
            typing_rate=12.0 if n > 300 else 4.0,
            mean_speed=0.9 if spaces < 0.05 else 0.5,
            path_jitter=0.02 if n > 200 else 0.12,
            hour_of_day=float(time.localtime().tm_hour),
            extra={"len_norm": min(1.0, n / 500.0), "digit_ratio": digits},
        )
        return self.observe(feats)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _distance(self, a: List[float], b: List[float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def _decide(self, risk: float) -> Tuple[str, str]:
        if risk >= self.freeze_threshold:
            return "freeze", "Operator mismatch — session freeze"
        if risk >= self.step_up_threshold:
            return "step_up", "Operator anomaly — step-up auth recommended"
        if risk >= self.bias_threshold:
            return "bias", "Mild operator drift — bias regulatory layer"
        return "pass", "Operator match"
