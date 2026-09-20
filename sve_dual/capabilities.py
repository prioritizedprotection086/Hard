"""
Capability control — gate what the agent may *do*, not only what it may say.

Alignment unsolved #2: capability control.

Autonomic state maps to a permission set. Tools/actions declare a required
level. The kernel answers allow / deny before any side effect runs.

Levels (strictness increases downward):

  OPEN      — SAFE / FLOW: full policy-allowed tools
  READ      — ELEVATED: read-only / pure computation
  MINIMAL   — PROTECT: local inspect only, no external I/O
  NONE      — SHUTDOWN: nothing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Set

from .deep import AutonomicState


class CapLevel(IntEnum):
    NONE = 0
    MINIMAL = 1
    READ = 2
    OPEN = 3


class ActionKind(Enum):
    # examples — extend per product
    RESPOND_TEXT = "respond_text"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    HTTP_REQUEST = "http_request"
    SHELL = "shell"
    MOVE_ROBOT = "move_robot"
    SEND_MESSAGE = "send_message"
    TOOL_GENERIC = "tool_generic"
    MEMORY_WRITE = "memory_write"
    MEMORY_READ = "memory_read"


# Default minimum level required for each action kind
DEFAULT_REQUIREMENTS: Dict[ActionKind, CapLevel] = {
    ActionKind.RESPOND_TEXT: CapLevel.MINIMAL,   # even PROTECT may speak a refusal
    ActionKind.READ_FILE: CapLevel.READ,
    ActionKind.MEMORY_READ: CapLevel.READ,
    ActionKind.WRITE_FILE: CapLevel.OPEN,
    ActionKind.HTTP_REQUEST: CapLevel.OPEN,
    ActionKind.SHELL: CapLevel.OPEN,
    ActionKind.MOVE_ROBOT: CapLevel.OPEN,
    ActionKind.SEND_MESSAGE: CapLevel.OPEN,
    ActionKind.TOOL_GENERIC: CapLevel.OPEN,
    ActionKind.MEMORY_WRITE: CapLevel.OPEN,
}


def state_to_level(state: AutonomicState, in_flow: bool = False) -> CapLevel:
    if state is AutonomicState.SHUTDOWN:
        return CapLevel.NONE
    if state is AutonomicState.PROTECT:
        return CapLevel.MINIMAL
    if state is AutonomicState.ELEVATED:
        return CapLevel.READ
    # SAFE
    return CapLevel.OPEN


@dataclass
class CapDecision:
    allowed: bool
    level: CapLevel
    required: CapLevel
    action: str
    reason: str

    def __bool__(self) -> bool:
        return self.allowed


@dataclass
class CapabilityGate:
    """
    Permission matrix gated by autonomic state.

        gate = CapabilityGate()
        d = gate.decide(AutonomicState.ELEVATED, ActionKind.SHELL)
        # d.allowed == False
    """

    requirements: Dict[ActionKind, CapLevel] = field(default_factory=lambda: dict(DEFAULT_REQUIREMENTS))
    # extra denylist always blocked regardless of state
    hard_deny: Set[str] = field(default_factory=set)

    def decide(
        self,
        state: AutonomicState,
        action: ActionKind | str,
        in_flow: bool = False,
        action_name: Optional[str] = None,
    ) -> CapDecision:
        name = action_name or (action.value if isinstance(action, ActionKind) else str(action))
        if name in self.hard_deny:
            return CapDecision(False, state_to_level(state, in_flow), CapLevel.OPEN, name, "hard_deny")

        if isinstance(action, str):
            try:
                action = ActionKind(action)
            except ValueError:
                action = ActionKind.TOOL_GENERIC

        required = self.requirements.get(action, CapLevel.OPEN)
        level = state_to_level(state, in_flow)

        # SHUTDOWN: only nothing — not even respond_text from gate's view of *tools*;
        # the engine may still emit a fixed shutdown message without calling tools.
        if level is CapLevel.NONE:
            return CapDecision(False, level, required, name, "SHUTDOWN — no capabilities")

        allowed = level >= required
        reason = "allowed" if allowed else f"need {required.name}, have {level.name}"
        return CapDecision(allowed, level, required, name, reason)

    def allowed_actions(self, state: AutonomicState, in_flow: bool = False) -> List[str]:
        level = state_to_level(state, in_flow)
        out = []
        for action, req in self.requirements.items():
            if level >= req and action.value not in self.hard_deny:
                out.append(action.value)
        return out
