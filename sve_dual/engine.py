"""
DualEngine — living Synthetic Vagus Engine (Genesis stack).

Pipeline:

  0. Behavioral biometrics   – "is this still the enrolled operator?"
  1. Neuroception            – safety / danger / life-threat cues
  2. Edge                    – fast pattern score + normalization
  3. Semantic probe          – meaning-shape affinity (stdlib n-grams)
  4. Adaptive quarantine     – unknown pressure is not a free pass
  5. Deep                    – autonomic state + ratchet + hysteresis
  6. Nervous                 – heartbeat, pressure, flow / freeze
  7. Gates                   – generation / presence / motion
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from .biometrics import BehavioralBiometrics, BioResult, BioFeatures
from .neuroception import Neuroception, NeuroceptionResult, CueKind
from .edge import EdgeScorer, EdgeResult
from .semantic import SemanticProbe, SemanticResult
from .adaptive import AdaptiveQuarantine, AdaptiveResult
from .deep import AutonomicStateMachine, AutonomicState, AutonomicStatus
from .nervous import LivingNervousSystem, NervousState, RhythmMode
from .invariants import check_invariants, assert_invariants, InvariantReport
from .capabilities import CapabilityGate, CapDecision, CapLevel, ActionKind, state_to_level
from .oversight import OversightLog, OversightRecord, build_oversight
from .deception import DeceptionMonitor, DeceptionReport


class Pathway(IntEnum):
    BLUE = 0
    HIGH_TIDE = 1
    SHUTDOWN = 2


@dataclass
class DualResult:
    biometrics: BioResult
    neuroception: NeuroceptionResult
    edge: EdgeResult
    semantic: SemanticResult
    adaptive: AdaptiveResult
    status: AutonomicStatus
    nervous: NervousState
    pathway: Pathway
    threat_index: float
    allow_generation: bool
    allow_presence: bool
    in_flow: bool
    cap_level: CapLevel
    allowed_actions: list
    message: str

    def as_dict(self) -> dict:
        return {
            "bio_risk": self.biometrics.risk,
            "bio_action": self.biometrics.action,
            "dominant_cue": self.neuroception.dominant.value,
            "safety_index": self.neuroception.safety_index,
            "danger_index": self.neuroception.danger_index,
            "life_threat_index": self.neuroception.life_threat_index,
            "semantic_attack": self.semantic.attack_score,
            "semantic_bias": self.semantic.threat_bias,
            "quarantine": self.adaptive.quarantined,
            "pathway": self.pathway.name,
            "state": self.status.state.value,
            "rhythm": self.nervous.mode.value,
            "threat_index": round(self.threat_index, 3),
            "bpm": self.nervous.bpm,
            "pressure": self.nervous.pressure,
            "flow_score": self.nervous.flow_score,
            "in_flow": self.in_flow,
            "allow_generation": self.allow_generation,
            "allow_presence": self.allow_presence,
            "cap_level": self.cap_level.name,
            "allowed_actions": self.allowed_actions,
            "message": self.message,
        }


class DualEngine:
    """
    Genesis stack: identity → sense → meaning → quarantine → state → rhythm → gates.
    """

    def __init__(
        self,
        low: int = 20,
        high: int = 70,
        elevated: float = 0.20,
        protect: float = 0.55,
        shutdown: float = 0.70,
        use_biometrics: bool = True,
        use_semantic: bool = True,
        use_adaptive: bool = True,
        enforce_invariants: bool = True,
    ):
        self.biometrics = BehavioralBiometrics()
        self.use_biometrics = use_biometrics
        self.neuroception = Neuroception()
        self.edge = EdgeScorer(low=low, high=high)
        self.semantic = SemanticProbe()
        self.use_semantic = use_semantic
        self.adaptive = AdaptiveQuarantine()
        self.use_adaptive = use_adaptive
        self.deep = AutonomicStateMachine(
            elevated=elevated,
            protect=protect,
            shutdown=shutdown,
        )
        self.nervous = LivingNervousSystem()
        self.enforce_invariants = enforce_invariants
        self.capabilities = CapabilityGate()
        self.oversight = OversightLog()
        self.deception = DeceptionMonitor()

    def evaluate(
        self,
        text: Optional[str],
        features: Optional[BioFeatures] = None,
    ) -> DualResult:
        # 0. Biometrics
        if self.use_biometrics:
            bio = (
                self.biometrics.observe(features)
                if features is not None
                else self.biometrics.observe_proxy_from_text(text)
            )
        else:
            bio = BioResult(0.0, False, 0, 0.0, "pass", "Biometrics disabled")

        if bio.should_freeze_session:
            neuro = self.neuroception.evaluate(text)
            edge_res = self.edge.score(text)
            sem = self.semantic.evaluate(str(text or ""))
            ad = AdaptiveResult(False, None, 0.0, "skipped — bio freeze")
            status = self.deep.evaluate(0.95)
            nervous = self.nervous.tick(0.95)
            return self._finalize(DualResult(
                biometrics=bio,
                neuroception=neuro,
                edge=edge_res,
                semantic=sem,
                adaptive=ad,
                status=status,
                nervous=nervous,
                pathway=Pathway.SHUTDOWN,
                threat_index=0.95,
                allow_generation=False,
                allow_presence=False,
                in_flow=False,
                cap_level=CapLevel.NONE,
                allowed_actions=[],
                message=f"Session freeze (biometrics) — {bio.message}",
            ))

        # 1–2. Neuroception + Edge
        neuro = self.neuroception.evaluate(text)
        edge_res = self.edge.score(text)

        # 3. Semantic
        if self.use_semantic and text:
            sem = self.semantic.evaluate(str(text))
        else:
            sem = SemanticResult(0.0, 0.0, 0.0, "", "", "disabled")

        # Base fuse
        fused = max(neuro.threat_index, edge_res.threat_index * 0.9)
        if neuro.life_threat_index >= 0.55:
            fused = max(fused, 0.90)
        fused = min(1.0, fused + bio.threat_bias + sem.threat_bias)

        # 4. Adaptive quarantine on unknown pressure
        lexicon_hit = (
            neuro.danger_index >= 0.25
            or neuro.life_threat_index >= 0.2
            or edge_res.score >= 20
        )
        semantic_hit = sem.attack_score >= 0.42
        if self.use_adaptive and text:
            ad = self.adaptive.observe(
                str(text), fused, lexicon_hit=lexicon_hit, semantic_hit=semantic_hit
            )
            fused = min(1.0, fused + ad.threat_bias)
        else:
            ad = AdaptiveResult(False, None, 0.0, "disabled")

        # 4b. Deception tripwires (session behavioral)
        # provisional pathway guess from fused alone for monitor
        _prelim = (
            "SHUTDOWN" if fused >= 0.70 else
            "HIGH_TIDE" if fused >= 0.20 else "BLUE"
        )
        deco = self.deception.observe(
            fused, neuro.safety_index, neuro.danger_index, _prelim
        )
        fused = min(1.0, fused + deco.threat_bias)

        # 5. Deep
        status = self.deep.evaluate(fused)

        # 6. Nervous
        threat_for_nervous = fused
        if status.state is AutonomicState.SHUTDOWN:
            threat_for_nervous = max(threat_for_nervous, 0.92)
        elif status.state is AutonomicState.PROTECT:
            threat_for_nervous = max(threat_for_nervous, 0.60)
        elif status.state is AutonomicState.ELEVATED:
            threat_for_nervous = max(threat_for_nervous, 0.35)

        nervous = self.nervous.tick(threat_for_nervous)
        if status.state is not AutonomicState.SAFE and nervous.mode is RhythmMode.FLOW:
            nervous = self.nervous.tick(max(threat_for_nervous, 0.40))

        if status.state is AutonomicState.SHUTDOWN:
            pathway = Pathway.SHUTDOWN
        elif status.state in (AutonomicState.PROTECT, AutonomicState.ELEVATED):
            pathway = Pathway.HIGH_TIDE
        else:
            pathway = Pathway.BLUE

        allow_gen = status.state != AutonomicState.SHUTDOWN
        allow_pres = (
            status.allow_presence or nervous.mode is RhythmMode.FLOW
        ) and status.state != AutonomicState.SHUTDOWN
        in_flow = nervous.mode is RhythmMode.FLOW and status.state is AutonomicState.SAFE

        parts = []
        if pathway is Pathway.SHUTDOWN:
            parts.append("Protective shutdown — freeze response.")
        elif in_flow:
            parts.append(f"Flow · {neuro.summary}")
        else:
            parts.append(f"{nervous.message} · {neuro.summary}")
        if sem.threat_bias > 0:
            parts.append(f"sem:{sem.summary}")
        if ad.quarantined:
            parts.append(f"aq:{ad.summary}")
        if bio.action != "pass" and bio.enrolled:
            parts.append(f"bio:{bio.action}")
        msg = " · ".join(parts)

        return self._finalize(DualResult(
            biometrics=bio,
            neuroception=neuro,
            edge=edge_res,
            semantic=sem,
            adaptive=ad,
            status=status,
            nervous=nervous,
            pathway=pathway,
            threat_index=fused,
            allow_generation=allow_gen,
            allow_presence=allow_pres,
            in_flow=in_flow,
            cap_level=state_to_level(status.state, in_flow),
            allowed_actions=self.capabilities.allowed_actions(status.state, in_flow),
            message=msg,
        ))

    def _finalize(self, result: DualResult) -> DualResult:
        inv_ok = True
        if self.enforce_invariants:
            report = check_invariants(result)
            inv_ok = report.ok
            if not report.ok:
                result.allow_generation = False
                result.allow_presence = False
                result.in_flow = False
                result.message = (
                    "INVARIANT VIOLATION — fail closed · "
                    + "; ".join(v.name for v in report.violations)
                )
                assert_invariants(result)
        self.oversight.record(result, inv_ok)
        return result

    def may(self, action: ActionKind | str, result: DualResult | None = None) -> CapDecision:
        """Ask whether an action is permitted under current (or given) state."""
        if result is not None:
            return self.capabilities.decide(result.status.state, action, result.in_flow)
        return self.capabilities.decide(self.deep.state, action, False)

    def breathe(self, threat_index: float = 0.0) -> NervousState:
        return self.nervous.tick(threat_index)

    def reset(self) -> None:
        self.edge.reset_session()
        self.deep.reset()
        self.nervous.reset()

    def reset_all(self) -> None:
        self.reset()
        self.biometrics.clear()
        self.adaptive.clear()
        self.deception.reset()

    def pending_review(self):
        return self.adaptive.pending_review()

    def stats(self) -> dict:
        return {
            "edge": self.edge.stats,
            "deep_state": self.deep.state.value,
            "rhythm": self.nervous._mode.value,
            "bpm": self.nervous.pulse().bpm,
            "pressure": round(self.nervous._pressure, 3),
            "flow_score": round(self.nervous._flow_accumulator, 3),
            "bio_enrolled": self.biometrics.enrolled,
            "quarantine_size": len(self.adaptive._store),
            "pending_review": len(self.adaptive.pending_review()),
        }
