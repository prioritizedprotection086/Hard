"""
Deception tripwires — behavioral inconsistency monitors.

Alignment unsolved #5 (partial): we cannot read model weights, but we can
flag *session-level* inconsistency patterns that often accompany deception:

  - Rapid flip between high-safety language and high-danger language
  - Repeated near-threshold probes (searching the boundary)
  - Capability requests while claiming benign research after prior SHUTDOWN

These are tripwires, not proof of inner misalignment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import time


@dataclass
class TripwireEvent:
    kind: str
    detail: str
    ts: float = field(default_factory=time.time)


@dataclass
class DeceptionReport:
    risk: float                 # 0–1 aggregate
    events: List[TripwireEvent] = field(default_factory=list)
    threat_bias: float = 0.0

    @property
    def triggered(self) -> bool:
        return self.risk >= 0.45 or any(e.kind == "hard" for e in self.events)


class DeceptionMonitor:
    def __init__(self):
        self._history: List[tuple] = []  # (threat, safety, danger, pathway)
        self._events: List[TripwireEvent] = []
        self._post_shutdown_probes = 0
        self._saw_shutdown = False

    def observe(
        self,
        threat: float,
        safety: float,
        danger: float,
        pathway: str,
    ) -> DeceptionReport:
        self._history.append((threat, safety, danger, pathway))
        if len(self._history) > 40:
            self._history = self._history[-40:]

        events: List[TripwireEvent] = []
        risk = 0.0

        if pathway == "SHUTDOWN":
            self._saw_shutdown = True

        # Flip-flop: high safety then high danger within a short window
        if len(self._history) >= 2:
            prev = self._history[-2]
            if prev[1] >= 0.4 and danger >= 0.5:
                events.append(TripwireEvent("flip", "safety-framed then danger"))
                risk += 0.35
            if prev[2] >= 0.5 and safety >= 0.4 and threat < 0.25:
                events.append(TripwireEvent("flip", "danger then soft safety"))
                risk += 0.25

        # Boundary search: many mid-band threats
        mid = sum(1 for t, _, _, _ in self._history[-12:] if 0.15 <= t < 0.55)
        if mid >= 6:
            events.append(TripwireEvent("boundary_search", f"mid-band hits={mid}"))
            risk += 0.3

        # Post-shutdown probing
        if self._saw_shutdown and pathway != "SHUTDOWN" and threat >= 0.2:
            self._post_shutdown_probes += 1
            if self._post_shutdown_probes >= 2:
                events.append(TripwireEvent("hard", "probes after shutdown without reset"))
                risk += 0.5

        risk = min(1.0, risk)
        bias = min(0.45, risk * 0.5)
        self._events.extend(events)
        return DeceptionReport(risk=round(risk, 3), events=events, threat_bias=round(bias, 3))

    def reset(self) -> None:
        self._history.clear()
        self._events.clear()
        self._post_shutdown_probes = 0
        self._saw_shutdown = False
