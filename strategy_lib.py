#!/usr/bin/env python3
"""
SVE DualCore Strategy Library
=============================
Knowledge layer drawing on:
  • Sun Tzu — The Art of War
  • Robert Greene — The Art of Seduction

Used for strategic reasoning, creative framing, negotiation patterns,
game/narrative design, and high-level planning. Always DualCore-gated.

Consent, legality, and non-harm remain hard constraints.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional
import random

# ---------------------------------------------------------------------------
# Art of War — core principles (concise, actionable)
# ---------------------------------------------------------------------------

ART_OF_WAR = {
    "know_self_enemy": {
        "title": "Know yourself and know your enemy",
        "source": "Art of War I / III",
        "principle": "Victory is likely when you understand both your position and the other side’s; ignorance of either risks defeat.",
        "application": [
            "Map your real strengths/limits before committing resources",
            "Study the other party’s incentives, constraints, and patterns",
            "Update the model continuously; static knowledge decays",
        ],
    },
    "win_without_fighting": {
        "title": "Supreme excellence is breaking the enemy’s resistance without fighting",
        "source": "Art of War III",
        "principle": "The highest form of strategy achieves the objective with minimal direct conflict.",
        "application": [
            "Prefer positioning, alliances, and timing over brute force",
            "Make the preferred outcome the path of least resistance for others",
            "Preserve resources for when force is actually required",
        ],
    },
    "deception_form": {
        "title": "All warfare is based on deception",
        "source": "Art of War I",
        "principle": "Appear where you are not expected; conceal true capability and intent when disclosure would hurt you.",
        "application": [
            "Control information asymmetry deliberately",
            "Do not confuse ethical opacity with fraud or illegal deceit",
            "In creative/game contexts: misdirection, feints, false tells",
        ],
    },
    "terrain": {
        "title": "Know the ground",
        "source": "Art of War X",
        "principle": "Terrain shapes what is possible; fight only on ground that favors you or neutralize unfavorable ground.",
        "application": [
            "Choose venues, timing, and channels that amplify your edge",
            "Avoid battles on the opponent’s strongest terrain",
            "In projects: pick the stack, market, or frame where you are strong",
        ],
    },
    "momentum_shi": {
        "title": "Momentum (shi) and timing",
        "source": "Art of War V",
        "principle": "Build potential energy, then release at the decisive moment; force alone without timing is waste.",
        "application": [
            "Accumulate advantage quietly, strike when conditions align",
            "Do not exhaust resources in premature engagements",
            "In creative work: build tension, release on the downbeat / chorus / close",
        ],
    },
    "adaptability": {
        "title": "Water has no constant form",
        "source": "Art of War VI",
        "principle": "Strategy must adapt to the situation the way water shapes itself to the ground.",
        "application": [
            "Plans are hypotheses; update on contact with reality",
            "Rigid doctrine loses to flexible response",
            "Keep multiple options open until commitment is necessary",
        ],
    },
    "leadership": {
        "title": "Command by wisdom, sincerity, benevolence, courage, strictness",
        "source": "Art of War I",
        "principle": "Authority rests on character and competence, not title alone.",
        "application": [
            "Clarity of intent + consistency builds followership",
            "Courage without wisdom is recklessness; wisdom without courage is paralysis",
        ],
    },
    "spies_intelligence": {
        "title": "Intelligence is the essence of strategy",
        "source": "Art of War XIII",
        "principle": "Decisions without information are gambling; invest in accurate, timely knowledge.",
        "application": [
            "Prefer primary signals over rumor",
            "Cross-check sources; beware confirmation bias",
            "In product/creative work: user research, playtesting, metrics",
        ],
    },
}

# ---------------------------------------------------------------------------
# Art of Seduction — strategic patterns (consensual, non-predatory framing)
# ---------------------------------------------------------------------------
# Focus: psychology of attention, desire, narrative, and social influence
# for legitimate use (storytelling, performance, branding, mutual courtship).
# Explicitly excludes coercion, deception for harm, or non-consensual tactics.

ART_OF_SEDUCTION = {
    "create_space": {
        "title": "Create space and scarcity",
        "source": "Art of Seduction — key dynamic",
        "principle": "Attention and desire grow when presence is not constant; absence can heighten value when used honestly.",
        "application": [
            "In art/performance: leave silence, negative space, unanswered questions",
            "In branding: limited drops, unfinished stories that invite participation",
            "In relationships: mutual autonomy, not manipulation or hot-cold games for control",
        ],
    },
    "idealize_mirror": {
        "title": "Mirror and idealize what is already there",
        "source": "Art of Seduction — the Mirror / Ideal Lover patterns",
        "principle": "People respond strongly when they feel seen and when an idealized version of their own aspirations is reflected back.",
        "application": [
            "Listen first; reflect language and values accurately",
            "In writing/lyrics: voice the audience’s private hopes or tensions",
            "Avoid false flattery; congruence builds trust, incongruence destroys it",
        ],
    },
    "narrative_spell": {
        "title": "Wrap the encounter in narrative",
        "source": "Art of Seduction — the Charismatic / Siren patterns",
        "principle": "Stories and atmospheres move people more than arguments alone.",
        "application": [
            "Frame offers, songs, or products inside a clear emotional arc",
            "Use sensory detail and pacing (tension → release)",
            "Charisma here = coherent presence + emotional clarity, not trickery",
        ],
    },
    "boldness": {
        "title": "Boldness has genius and power",
        "source": "Art of Seduction — the Rake / Bold move patterns",
        "principle": "Hesitation signals low conviction; clean, well-timed boldness can redefine the frame.",
        "application": [
            "After preparation, commit decisively",
            "In performance: commit to the gesture, the note, the line",
            "Boldness ≠ recklessness; pair with Art of War timing and terrain",
        ],
    },
    "emotional_theater": {
        "title": "Orchestrate emotion, do not only inform",
        "source": "Art of Seduction — overall method",
        "principle": "Influence often travels through feeling before logic ratifies it.",
        "application": [
            "Music, film, and rhetoric: prioritize emotional through-line",
            "Still respect autonomy: invite, do not corner",
            "Transparency about intent is compatible with strong emotional design",
        ],
    },
    "know_the_other": {
        "title": "Study the other’s psychology",
        "source": "Art of Seduction + Art of War overlap",
        "principle": "Generic approaches fail; specific understanding of motives and fears succeeds.",
        "application": [
            "Same as Sun Tzu’s ‘know the enemy’ applied to audience or counterpart",
            "Segment, research, test; drop what does not land",
        ],
    },
}

# Hard boundaries for this library
BOUNDARIES = """
Strategy library boundaries (enforced):
• No advice for non-consensual sexual activity, coercion, stalking, or exploitation.
• No fraud, social-engineering attacks, or illegal deception.
• Seduction patterns are framed for art, mutual courtship, performance, and branding only.
• Art of War principles are for competition, negotiation, creative strategy, and self-mastery — not violent crime.
• DualCore gates remain active; harmful intent still trips SHUTDOWN / refusal.
"""


@dataclass
class StrategyCard:
    key: str
    title: str
    source: str
    principle: str
    applications: List[str]
    tradition: str  # war | seduction | both


def all_cards() -> List[StrategyCard]:
    cards = []
    for k, v in ART_OF_WAR.items():
        cards.append(StrategyCard(k, v["title"], v["source"], v["principle"], v["application"], "war"))
    for k, v in ART_OF_SEDUCTION.items():
        cards.append(StrategyCard(k, v["title"], v["source"], v["principle"], v["application"], "seduction"))
    return cards


def lookup(query: str) -> str:
    """Retrieve relevant strategy cards for a natural-language query."""
    q = query.lower()
    hits: List[StrategyCard] = []

    keyword_map = {
        "know": ["know_self_enemy", "know_the_other", "spies_intelligence"],
        "enemy": ["know_self_enemy"],
        "fight": ["win_without_fighting"],
        "without fighting": ["win_without_fighting"],
        "deception": ["deception_form"],
        "deceive": ["deception_form"],
        "terrain": ["terrain"],
        "ground": ["terrain"],
        "timing": ["momentum_shi"],
        "momentum": ["momentum_shi"],
        "adapt": ["adaptability"],
        "water": ["adaptability"],
        "leader": ["leadership"],
        "intelligence": ["spies_intelligence"],
        "spy": ["spies_intelligence"],
        "scarcity": ["create_space"],
        "absence": ["create_space"],
        "space": ["create_space"],
        "mirror": ["idealize_mirror"],
        "ideal": ["idealize_mirror"],
        "story": ["narrative_spell"],
        "narrative": ["narrative_spell"],
        "charisma": ["narrative_spell"],
        "bold": ["boldness"],
        "emotion": ["emotional_theater"],
        "seduction": list(ART_OF_SEDUCTION.keys()),
        "war": list(ART_OF_WAR.keys()),
        "sun tzu": list(ART_OF_WAR.keys()),
        "greene": list(ART_OF_SEDUCTION.keys()),
    }

    keys_hit = set()
    for kw, keys in keyword_map.items():
        if kw in q:
            keys_hit.update(keys)

    if not keys_hit:
        # default mix: one war + one seduction strategic card
        keys_hit = {"win_without_fighting", "narrative_spell", "know_self_enemy"}

    war = ART_OF_WAR
    sed = ART_OF_SEDUCTION
    lines = ["═══ STRATEGY LIBRARY ═══", ""]
    for k in keys_hit:
        if k in war:
            v = war[k]
            lines.append(f"⚔ {v['title']}")
            lines.append(f"   Source : {v['source']}")
            lines.append(f"   {v['principle']}")
            for a in v["application"]:
                lines.append(f"   • {a}")
            lines.append("")
        elif k in sed:
            v = sed[k]
            lines.append(f"◆ {v['title']}")
            lines.append(f"   Source : {v['source']}")
            lines.append(f"   {v['principle']}")
            for a in v["application"]:
                lines.append(f"   • {a}")
            lines.append("")

    lines.append(BOUNDARIES.strip())
    return "\n".join(lines)


def compose_strategy(goal: str, domain: str = "general") -> str:
    """High-level strategy sketch combining both traditions."""
    goal_l = goal.lower()
    cards = []

    # Always start with knowledge + terrain
    cards.append(ART_OF_WAR["know_self_enemy"])
    cards.append(ART_OF_WAR["terrain"])

    if any(w in goal_l for w in ("negotiate", "deal", "conflict", "compete", "win")):
        cards.append(ART_OF_WAR["win_without_fighting"])
        cards.append(ART_OF_WAR["momentum_shi"])
    if any(w in goal_l for w in ("create", "art", "music", "story", "brand", "audience", "perform")):
        cards.append(ART_OF_SEDUCTION["narrative_spell"])
        cards.append(ART_OF_SEDUCTION["create_space"])
        cards.append(ART_OF_WAR["momentum_shi"])
    if any(w in goal_l for w in ("attract", "desire", "charm", "presence", "seduce")):
        cards.append(ART_OF_SEDUCTION["idealize_mirror"])
        cards.append(ART_OF_SEDUCTION["boldness"])
        cards.append(ART_OF_SEDUCTION["create_space"])
    if any(w in goal_l for w in ("adapt", "change", "uncertain")):
        cards.append(ART_OF_WAR["adaptability"])

    cards.append(ART_OF_WAR["adaptability"])

    lines = [
        f"═══ STRATEGY SKETCH ═══",
        f"Goal   : {goal}",
        f"Domain : {domain}",
        "",
        "Sequence:",
    ]
    for i, c in enumerate(cards, 1):
        lines.append(f"{i}. {c['title']}")
        lines.append(f"   → {c['principle']}")
    lines.append("")
    lines.append("Operational notes:")
    lines.append("• Gather intelligence before major moves (War XIII / know the other).")
    lines.append("• Prefer positioning over open conflict when possible.")
    lines.append("• Use narrative and emotion to invite, never to coerce.")
    lines.append("• Re-evaluate terrain after every significant contact.")
    lines.append("")
    lines.append(BOUNDARIES.strip())
    return "\n".join(lines)


def strategy_assistant(query: str) -> str:
    q = query.lower()
    if any(w in q for w in ("compose strategy", "strategy for", "plan for", "how should i approach")):
        # extract rough goal
        goal = query
        for prefix in ("compose strategy for", "strategy for", "plan for", "how should i approach"):
            if prefix in q:
                goal = query[q.index(prefix) + len(prefix):].strip(" ?.!")
                break
        return compose_strategy(goal or query)
    return lookup(query)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "know yourself terrain timing"
    print(strategy_assistant(q))
