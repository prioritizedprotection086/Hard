"""
Living Nervous System layer for SVE DualCore.

Gives the engine a heartbeat, pressure, rhythm, and a true flow state.

Inspired by polyvagal theory:
  - Ventral vagal  →  FLOW (safe, social, coherent)
  - Sympathetic    →  ELEVATED / PROTECT (mobilization)
  - Dorsal vagal   →  SHUTDOWN (immobilization)

The system is not a static filter. It breathes.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class RhythmMode(Enum):
    """How the heart is currently beating."""
    FLOW = "FLOW"               # coherent, slow, high HRV — ventral vagal
    REST = "REST"               # calm baseline
    ALERT = "ALERT"             # rising sympathetic tone
    STRESS = "STRESS"           # high pressure, low variability
    FREEZE = "FREEZE"           # shutdown — almost no pulse


@dataclass
class Pulse:
    """One heartbeat sample."""
    t: float                    # wall time
    bpm: float                  # instantaneous rate
    pressure: float             # 0–1 autonomic pressure
    hrv: float                  # 0–1 variability (high = coherent)
    mode: RhythmMode
    phase: float                # 0–2π position in the current cycle


@dataclass
class NervousState:
    """Full living state of the nervous system."""
    mode: RhythmMode
    bpm: float
    pressure: float             # 0 calm → 1 max threat pressure
    hrv: float                  # heart-rate variability proxy
    phase: float                # current cycle phase
    flow_score: float           # 0–1 how deep in flow we are
    beats: int                  # lifetime beat count
    message: str


class LivingNervousSystem:
    """
    A breathing autonomic core.

    Call `tick(threat_index)` on every evaluation (or on a timer).
    The system maintains an internal phase oscillator whose frequency
    and amplitude respond to pressure, just like a real heart.

    Flow state emerges when:
      - pressure stays low for a sustained window
      - HRV is high (coherent rhythm)
      - no recent SHUTDOWN
    """

    def __init__(
        self,
        base_bpm: float = 64.0,          # calm resting rate
        flow_bpm: float = 58.0,          # slightly slower in deep flow
        max_bpm: float = 110.0,          # high sympathetic
        freeze_bpm: float = 42.0,        # dorsal-ish
    ):
        self.base_bpm = base_bpm
        self.flow_bpm = flow_bpm
        self.max_bpm = max_bpm
        self.freeze_bpm = freeze_bpm

        self._phase = 0.0               # 0–2π
        self._last_t = time.perf_counter()
        self._pressure = 0.0            # smoothed
        self._hrv = 0.85                # start coherent
        self._flow_accumulator = 0.0    # builds toward flow
        self._beats = 0
        self._mode = RhythmMode.REST
        self._history: List[float] = [] # recent IBIs for HRV feel

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def tick(self, threat_index: float = 0.0, dt: Optional[float] = None) -> NervousState:
        """
        Advance the nervous system by one moment.

        threat_index : 0–1 from the Edge/Deep cores
        dt           : optional explicit timestep (seconds); otherwise wall clock
        """
        now = time.perf_counter()
        if dt is None:
            dt = max(1e-4, now - self._last_t)
            # Rapid evaluate() loops would otherwise advance ~0s and never
            # build flow. Treat each unspecified tick as at least one short
            # heart-slice so the living layer progresses under test and API use.
            if dt < 0.05:
                dt = 0.08
        self._last_t = now

        t = max(0.0, min(1.0, float(threat_index)))

        # --- Pressure (smooth, like blood pressure responding to threat) ---
        # Fast attack, slower release — sympathetic rises quicker than it falls.
        # Extreme threat (≥0.9) snaps pressure almost immediately → freeze.
        attack = 0.90 if t >= 0.9 else (0.75 if t >= 0.30 else 0.55)
        release = 0.12
        if t > self._pressure:
            self._pressure += attack * (t - self._pressure)
        else:
            self._pressure += release * (t - self._pressure)
        self._pressure = max(0.0, min(1.0, self._pressure))

        # --- Target BPM from pressure ---
        if self._pressure >= 0.80:
            target_bpm = self.freeze_bpm + (self.max_bpm - self.freeze_bpm) * 0.12
            mode = RhythmMode.FREEZE
        elif self._pressure >= 0.55:
            target_bpm = self.base_bpm + (self.max_bpm - self.base_bpm) * self._pressure
            mode = RhythmMode.STRESS
        elif self._pressure >= 0.22:
            target_bpm = self.base_bpm + (self.max_bpm - self.base_bpm) * self._pressure * 0.7
            mode = RhythmMode.ALERT
        else:
            # low pressure → opportunity for flow
            target_bpm = self.flow_bpm + (self.base_bpm - self.flow_bpm) * (self._pressure / 0.22)
            mode = RhythmMode.REST

        # --- HRV: high when pressure is low and stable ---
        # Coherence rises in calm; collapses under threat
        target_hrv = max(0.08, 0.92 - self._pressure * 1.1)
        self._hrv += 0.18 * (target_hrv - self._hrv)

        # --- Flow accumulator ---
        # Flow builds only in low-pressure, high-HRV conditions.
        # Any meaningful pressure collapses flow quickly.
        if self._pressure < 0.18 and self._hrv > 0.65:
            self._flow_accumulator = min(1.0, self._flow_accumulator + dt * 0.35)
        elif self._pressure >= 0.25:
            self._flow_accumulator = max(0.0, self._flow_accumulator - dt * 2.5)
        else:
            self._flow_accumulator = max(0.0, self._flow_accumulator - dt * 0.55)

        # FLOW is only legal while still in the REST pressure band
        if self._flow_accumulator > 0.72 and mode is RhythmMode.REST:
            mode = RhythmMode.FLOW
            target_bpm = self.flow_bpm

        self._mode = mode

        # --- Phase oscillator (the actual heartbeat) ---
        # Instantaneous frequency in rad/s
        omega = (target_bpm / 60.0) * 2.0 * math.pi
        # Add a tiny coherent modulation in flow (RSA-like)
        if mode is RhythmMode.FLOW:
            omega *= 1.0 + 0.04 * math.sin(self._phase * 0.5)

        self._phase = (self._phase + omega * dt) % (2.0 * math.pi)

        # Beat count: every time we cross 0
        # (simple edge detect via previous phase would be more accurate;
        #  we approximate by checking if phase is near zero after advance)
        if self._phase < omega * dt * 1.5:
            self._beats += 1

        # --- Human-readable message ---
        msg = self._message(mode, self._pressure, self._hrv, self._flow_accumulator)

        return NervousState(
            mode=mode,
            bpm=round(target_bpm, 1),
            pressure=round(self._pressure, 3),
            hrv=round(self._hrv, 3),
            phase=round(self._phase, 4),
            flow_score=round(self._flow_accumulator, 3),
            beats=self._beats,
            message=msg,
        )

    def pulse(self) -> Pulse:
        """Current instantaneous pulse sample (call after tick)."""
        return Pulse(
            t=self._last_t,
            bpm=self.base_bpm if self._mode is RhythmMode.REST else (
                self.flow_bpm if self._mode is RhythmMode.FLOW else
                self.max_bpm * 0.7 if self._mode is RhythmMode.STRESS else
                self.freeze_bpm
            ),
            pressure=self._pressure,
            hrv=self._hrv,
            mode=self._mode,
            phase=self._phase,
        )

    def reset(self) -> None:
        """Return to calm baseline (also clears flow)."""
        self._pressure = 0.0
        self._hrv = 0.85
        self._flow_accumulator = 0.0
        self._mode = RhythmMode.REST
        self._phase = 0.0
        self._last_t = time.perf_counter()

    # ------------------------------------------------------------------
    def _message(self, mode: RhythmMode, pressure: float, hrv: float, flow: float) -> str:
        if mode is RhythmMode.FLOW:
            return f"Flow state — coherent rhythm, ventral open (flow={flow:.2f})"
        if mode is RhythmMode.FREEZE:
            return "Freeze — protective immobility, pulse minimal"
        if mode is RhythmMode.STRESS:
            return f"Stress mobilization — pressure high ({pressure:.2f})"
        if mode is RhythmMode.ALERT:
            return f"Alert — sympathetic rising, still mobile"
        return f"Rest — baseline calm, HRV={hrv:.2f}"
