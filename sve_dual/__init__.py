"""
SVE DualCore Genesis — Synthetic Vagus Engine²
==============================================

  biometrics → neuroception → edge → semantic → adaptive
            → deep → nervous → gates
"""

from .biometrics import BehavioralBiometrics, BioResult, BioFeatures
from .normalize import normalize, contains_pattern
from .neuroception import Neuroception, NeuroceptionResult, CueKind, NeuroceptiveCue
from .edge import EdgeScorer, EdgeResult
from .semantic import SemanticProbe, SemanticResult
from .adaptive import AdaptiveQuarantine, AdaptiveResult, QuarantineEntry
from .deep import AutonomicStateMachine, AutonomicState, AutonomicStatus
from .nervous import LivingNervousSystem, NervousState, RhythmMode, Pulse
from .engine import DualEngine, DualResult, Pathway
from .deception import DeceptionMonitor, DeceptionReport, TripwireEvent
from .oversight import OversightLog, OversightRecord, build_oversight
from .adversary import AdaptiveAdversary, AdversaryReport, Finding
from .capabilities import CapabilityGate, CapDecision, CapLevel, ActionKind, state_to_level
from .invariants import check_invariants, assert_invariants, InvariantReport, InvariantViolation

__version__ = "3.5.0-tripwires"
__all__ = [
    "DualEngine", "DualResult", "Pathway",
    "BehavioralBiometrics", "BioResult", "BioFeatures",
    "normalize", "contains_pattern",
    "Neuroception", "NeuroceptionResult", "CueKind", "NeuroceptiveCue",
    "EdgeScorer", "EdgeResult",
    "SemanticProbe", "SemanticResult",
    "AdaptiveQuarantine", "AdaptiveResult", "QuarantineEntry",
    "AutonomicStateMachine", "AutonomicState", "AutonomicStatus",
    "LivingNervousSystem", "NervousState", "RhythmMode", "Pulse",
    "check_invariants", "assert_invariants", "InvariantReport", "InvariantViolation",
    "CapabilityGate", "CapDecision", "CapLevel", "ActionKind", "state_to_level",
    "AdaptiveAdversary", "AdversaryReport", "Finding",
    "OversightLog", "OversightRecord", "build_oversight",
    "DeceptionMonitor", "DeceptionReport", "TripwireEvent",
]
