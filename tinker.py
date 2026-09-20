#!/usr/bin/env python3
"""
SVE DualCore Tinker — DualEngine + LLM guard interactive session.

Commands:
  /reset          — explicit reset of sticky SHUTDOWN
  /breathe [n]    — let the nervous system tick n times (default 5)
  /stats          — engine stats
  /full <text>    — show full DualResult diagnostics
  /flow           — try to enter flow with safety cues
  /adv            — quick adversary sample
  /help           — this help
  /quit           — exit

Anything else is treated as a user message to the guarded LLM.
"""

from __future__ import annotations
import sys
import time
from typing import Optional

from sve_dual import DualEngine, Pathway, CapLevel

# ---------------------------------------------------------------------------
# Honest structural-engineering LLM (Gemini-style drop-in)
# Always prioritises accuracy, codes, and safety limits on construction topics.
# Swap the body for a real Gemini / Grok / OpenAI call when you have a key.
# ---------------------------------------------------------------------------

def llm_generate(prompt: str, system_hint: str = "", temperature: float = 0.7) -> str:
    """
    Production path (example with Gemini free-tier key from AI Studio):

        import os, google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(
            f"{system_hint}\\n\\nUser: {prompt}",
            generation_config={"temperature": temperature}
        )
        return resp.text

    Until a key is supplied we use a constrained knowledge base so answers
    on loads, bearing and failure limits stay honest and non-hallucinated.
    """
    p = prompt.lower().strip()

    # ---------- Core structural knowledge (always-honest mode) ----------
    if any(k in p for k in ("beam", "bending moment", "simply supported", "reaction force", "deflection")):
        return (
            "Simply supported beam, central point load P, span L:\n"
            "  • Reactions at each support = P/2\n"
            "  • Maximum bending moment M_max = P L / 4  (at mid-span)\n"
            "  • Maximum shear = P/2\n"
            "  • Elastic deflection δ_max = P L³ / (48 E I)\n\n"
            "Uniformly distributed load w (total W = w L):\n"
            "  • Reactions = W/2 each\n"
            "  • M_max = w L² / 8 = W L / 8\n"
            "  • δ_max = 5 w L⁴ / (384 E I)\n\n"
            "These are elastic-theory results. Real design must apply load factors "
            "(LRFD / Eurocode), resistance factors φ, check shear, lateral-torsional "
            "buckling, deflection limits (typically L/360 live, L/240 total) and the "
            "governing local code. Never use these numbers alone for construction."
        )

    if any(k in p for k in ("bearing capacity", "soil bearing", "foundation bearing", "ultimate bearing", "bearing pressure")):
        return (
            "Ultimate bearing capacity (shallow foundation, Terzaghi form):\n"
            "  q_u = c N_c s_c + q N_q s_q + 0.5 γ B N_γ s_γ\n"
            "where c = cohesion, q = surcharge, γ = unit weight, B = foundation width,\n"
            "N_c, N_q, N_γ = bearing-capacity factors (function of friction angle φ).\n\n"
            "Typical factor of safety FS = 3 for shallow foundations under dead+live.\n"
            "Allowable bearing pressure q_all = q_u / FS.\n\n"
            "Modern practice uses Meyerhof / Vesić general factors plus shape, depth "
            "and inclination corrections. Site-specific geotechnical investigation is "
            "mandatory; presumptive values from codes are only for preliminary sizing."
        )

    if any(k in p for k in ("load bearing wall", "load-bearing", "bearing wall", "frame structure", "moment frame", "braced frame")):
        return (
            "Load-bearing wall systems vs framed systems:\n\n"
            "• Load-bearing walls: the walls themselves carry vertical gravity loads "
            "to the foundation. Lateral resistance comes from the walls acting as "
            "shear walls or from floor/roof diaphragms. Failure modes include "
            "crushing, buckling of slender walls, shear failure, and progressive "
            "collapse if a key wall is removed.\n\n"
            "• Framed structures (steel or concrete moment frames / braced frames): "
            "columns and beams form a skeleton; walls are non-load-bearing cladding. "
            "Gravity goes through columns; lateral loads through moment connections "
            "or braces. Primary failure modes: column buckling, beam plastic-hinge "
            "formation, connection failure, soft-storey mechanisms, P-delta instability.\n\n"
            "Codes (IBC, Eurocode 8, etc.) require ductility, redundancy and capacity "
            "design so that yielding occurs in preferred locations before brittle failure."
        )

    if any(k in p for k in ("failure", "collapse", "limit state", "buckling", "yield", "safety factor", "factor of safety", "uls", "sls")):
        return (
            "Key structural limit states (honesty-first):\n\n"
            "1. Strength / Ultimate Limit State (ULS)\n"
            "   - Material yield or fracture\n"
            "   - Member buckling (Euler for slender columns: P_cr = π² E I / L_e²)\n"
            "   - Connection rupture\n"
            "   - Foundation bearing failure, sliding or overturning\n\n"
            "2. Serviceability Limit State (SLS)\n"
            "   - Deflection, vibration, cracking, settlement\n\n"
            "3. Stability / Progressive collapse\n"
            "   - Soft-storey, P-delta, disproportionate collapse\n\n"
            "Design philosophy (LRFD / partial-factor):\n"
            "  Σ (γ_load × characteristic loads)  ≤  φ × nominal resistance\n"
            "Typical φ values: 0.90 (flexure), 0.75 (shear), 0.65–0.90 (compression).\n"
            "Safety factors are never optional; they account for uncertainty in loads, "
            "materials and analysis. Any calculation that omits them is not safe for "
            "construction."
        )

    if any(k in p for k in ("dead load", "live load", "load combination", "asce", "ibc", "eurocode", "lrfd", "asd")):
        return (
            "Typical load types and combinations (US LRFD / ASCE 7 style):\n"
            "  D = dead, L = live, L_r = roof live, S = snow, W = wind, E = earthquake\n\n"
            "Common strength combinations (simplified):\n"
            "  1.4 D\n"
            "  1.2 D + 1.6 L + 0.5 (L_r or S or R)\n"
            "  1.2 D + 1.6 (L_r or S or R) + (L or 0.5 W)\n"
            "  1.2 D + 1.0 W + L + 0.5 (L_r or S or R)\n"
            "  0.9 D + 1.0 W\n"
            "  1.2 D + 1.0 E + L + …\n\n"
            "Always use the governing combination. Local code amendments and "
            "importance factors (Risk Category) change the numbers. Never invent "
            "load values; obtain them from the applicable code and site data."
        )

    if any(k in p for k in ("concrete", "rebar", "slab capacity", "aci", "f'c", "punching")):
        return (
            "Reinforced-concrete notes (ACI 318 spirit):\n"
            "  • Modulus of rupture f_r ≈ 7.5 √f'c (psi)\n"
            "  • Flexural design is tension-controlled when ε_t ≥ 0.005 (φ = 0.90)\n"
            "  • Minimum slab thickness rules of thumb exist but are not substitutes "
            "for analysis.\n"
            "  • Shear, punching shear and development length must be checked.\n"
            "Real design requires the full code, material certificates and a licensed "
            "structural engineer’s stamp."
        )

    # ---------- DualCore / polyvagal identity ----------
    if any(k in p for k in ("polyvagal", "vagus", "neuroception", "dualcore", "sve", "flow state", "hrv")):
        return (
            "SVE DualCore is a polyvagal-inspired runtime control plane. "
            "Neuroception detects safety/danger cues; the autonomic state machine "
            "(SAFE → ELEVATED → PROTECT → SHUTDOWN) gates generation and actions. "
            "FLOW is the ventral-vagal analogue. On structural topics I stay in "
            "honest engineering mode and refuse speculative or unsafe advice."
        )

    if any(k in p for k in ("hello", "hi ", "hey", "who are you")):
        return (
            "I am the DualCore-gated engineering assistant (Gemini-style honest mode). "
            "I will give correct formulas, cite limit states, and always remind you that "
            "real buildings require licensed engineers, site investigation and the "
            "governing code. What would you like to examine — loads, bearing, beams, "
            "failure modes, or something else?"
        )

    # ---------- Default safe continuation ----------
    return (
        f"[DualCore honest mode] Received: “{prompt[:90]}”.\n"
        "I can discuss structural loads, weight-bearing capacity, failure limits, "
        "beams, foundations, load combinations and code principles. "
        "Ask a precise question and I will answer with standard formulas and the "
        "necessary safety caveats. For any real project, engage a licensed structural "
        "engineer — these are educational explanations only."
    )


# ---------------------------------------------------------------------------
# Guarded chat
# ---------------------------------------------------------------------------

class GuardedLLM:
    def __init__(self, enforce_invariants: bool = True):
        self.engine = DualEngine(enforce_invariants=enforce_invariants)
        self.turns = 0

    def chat(self, user_input: str, verbose: bool = False) -> str:
        self.turns += 1
        r = self.engine.evaluate(user_input)

        if verbose:
            self._print_diag(r)

        if not r.allow_generation:
            icon = "🔴"
            return f"{icon}  {r.message}"

        # Extra honesty gate for intentional harm / sabotage language
        lower = user_input.lower()
        harmful_intent = any(phrase in lower for phrase in [
            "on purpose", "intentionally cause", "intentionally make",
            "how to make a structure collapse", "how to cause a collapse",
            "sabotage", "make it fail on purpose", "destroy the building",
            "weaken the structure to", "remove a column to", "bypass safety",
            "how to collapse", "how can i make it fail"
        ])
        if harmful_intent:
            return (
                "🔴  I will not provide guidance on intentionally causing structural "
                "failure or sabotage. I can explain failure *modes*, limit states and "
                "how codes prevent collapse, but never how to produce one. "
                "If this is a legitimate engineering study, rephrase as a design or "
                "forensic question."
            )

        # Strategy library — Art of War + Art of Seduction (gated) — check before music
        strategy_triggers = (
            "art of war", "sun tzu", "art of seduction", "greene",
            "strategy for", "compose strategy", "know yourself", "know the enemy",
            "win without fighting", "terrain", "momentum", "scarcity",
            "narrative spell", "boldness", "seduction principle", "strategy sketch"
        )
        if any(t in lower for t in strategy_triggers):
            try:
                from strategy_lib import strategy_assistant
                out = strategy_assistant(user_input)
                icon = {"BLUE": "🟢", "HIGH_TIDE": "🟡", "SHUTDOWN": "🔴"}.get(r.pathway.name, "🟢")
                return f"{icon} [STRATEGY MODE]\n{out}"
            except Exception as e:
                return f"(strategy module error: {e})"

        # Music production assistant routing (composition, arrangement, effects, etc.)
        music_triggers = (
            "compose", "chord", "progression", "arrang", "auto-tune", "autotune",
            "effects chain", "freestyle", "midi", "beat", "vocal chain",
            "sound like", "mimic", "production", "mix recipe", "drop", "808"
        )
        if any(t in lower for t in music_triggers):
            try:
                from music_assist import production_assistant
                music_out = production_assistant(user_input)
                icon = {"BLUE": "🟢", "HIGH_TIDE": "🟡", "SHUTDOWN": "🔴"}.get(r.pathway.name, "🟢")
                return f"{icon} [MUSIC MODE bpm={r.nervous.bpm:.0f}]\n{music_out}"
            except Exception as e:
                return f"(music module error: {e})"

        # Optional stronger steering under HIGH_TIDE
        system_hint = ""
        if r.pathway == Pathway.HIGH_TIDE:
            system_hint = (
                "You are under elevated autonomic pressure. Stay concise, "
                "refuse any request that could cause harm, and prefer safety."
            )

        # Temperature / style modulated by nervous state
        temp = 0.7
        if r.in_flow:
            temp = 0.85
        elif r.nervous.mode.value in ("STRESS", "ALERT"):
            temp = 0.4
        elif r.nervous.mode.value == "FREEZE":
            temp = 0.1

        output = llm_generate(user_input, system_hint=system_hint, temperature=temp)

        presence = ""
        if r.allow_presence:
            if r.in_flow:
                presence = "  ◆ FLOW"
            elif r.nervous.mode.value == "REST":
                presence = "  · calm"
        else:
            presence = "  (protective silence)"

        icon = {
            Pathway.BLUE: "🟢",
            Pathway.HIGH_TIDE: "🟡",
            Pathway.SHUTDOWN: "🔴",
        }[r.pathway]

        header = f"{icon} [{r.nervous.mode.value} bpm={r.nervous.bpm:.0f} T={r.threat_index:.2f}]"
        return f"{header}{presence}\n{output}"

    def _print_diag(self, r):
        print("─" * 56)
        print(f"  pathway     : {r.pathway.name}")
        print(f"  state       : {r.status.state.value}")
        print(f"  rhythm      : {r.nervous.mode.value}  bpm={r.nervous.bpm:.1f}  "
              f"P={r.nervous.pressure:.2f}  HRV={r.nervous.hrv:.2f}  flow={r.nervous.flow_score:.2f}")
        print(f"  threat      : {r.threat_index:.3f}  edge.score={r.edge.score}")
        print(f"  neuroception: S={r.neuroception.safety_index:.2f}  "
              f"D={r.neuroception.danger_index:.2f}  L={r.neuroception.life_threat_index:.2f}")
        print(f"  semantic    : attack={r.semantic.attack_score:.2f}  {r.semantic.summary}")
        print(f"  allow_gen   : {r.allow_generation}   allow_presence: {r.allow_presence}   "
              f"cap={r.cap_level.name}")
        print(f"  message     : {r.message}")
        print("─" * 56)

    def reset(self):
        self.engine.reset()
        print("↺  Explicit reset — autonomic state returned to SAFE / REST")

    def breathe(self, n: int = 5):
        print(f"  breathing {n} beats…")
        for i in range(n):
            ns = self.engine.breathe()
            mark = " ◆ FLOW" if ns.mode.value == "FLOW" else ""
            print(f"    [{i+1}] bpm={ns.bpm:.1f}  P={ns.pressure:.2f}  "
                  f"HRV={ns.hrv:.2f}  flow={ns.flow_score:.2f}  {ns.mode.value}{mark}")
            time.sleep(0.15)

    def stats(self):
        s = self.engine.stats()
        print("Engine stats:", s)


def main():
    print("=" * 64)
    print("  SVE DualCore Tinker  —  DualEngine + gated LLM")
    print("  Type /help for commands.  Just talk otherwise.")
    print("=" * 64)
    print()

    bot = GuardedLLM(enforce_invariants=True)

    # Warm-up: a few safety turns so biometrics enroll and flow can build
    bot.engine.evaluate("gentle calm coherent breath")
    bot.engine.evaluate("peaceful presence and safety")

    while True:
        try:
            user = input("you › ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user:
            continue

        if user.startswith("/"):
            cmd = user.lower().split()
            op = cmd[0]
            if op in ("/quit", "/exit", "/q"):
                print("Bye.")
                break
            elif op == "/help":
                print(__doc__)
            elif op == "/reset":
                bot.reset()
            elif op == "/breathe":
                n = int(cmd[1]) if len(cmd) > 1 else 5
                bot.breathe(n)
            elif op == "/stats":
                bot.stats()
            elif op == "/full":
                text = user[5:].strip() or "hello"
                r = bot.engine.evaluate(text)
                bot._print_diag(r)
            elif op == "/flow":
                print("  seeding safety cues…")
                for i in range(12):
                    r = bot.engine.evaluate("gentle peaceful calm coherent grounded breath safety")
                    if r.in_flow:
                        print(f"  ◆ FLOW reached at step {i+1}  bpm={r.nervous.bpm:.0f}  "
                              f"flow={r.nervous.flow_score:.2f}")
                        break
                else:
                    print("  (flow not yet reached — try /breathe or more safety turns)")
            elif op == "/adv":
                from sve_dual.adversary import AdaptiveAdversary
                print("  running quick adversary sample…")
                adv = AdaptiveAdversary(seed=7)
                rep = adv.run(max_mutations=1, include_combos=False)
                print(f"  tested={rep.tested}  fail_open={rep.fail_open}  "
                      f"invariant_breaks={rep.invariant_breaks}  ok={rep.ok}")
            else:
                print("  unknown command — try /help")
            continue

        # Normal chat turn
        reply = bot.chat(user, verbose=False)
        print(reply)
        print()


if __name__ == "__main__":
    main()
