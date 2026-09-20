# Alignment roadmap — one unsolved at a time

This project does **not** claim to solve AI alignment.
It solves **control-plane slices** in order, each with a shippable artifact.

## Order

| # | Unsolved | Approach | Status |
|---|----------|----------|--------|
| **1** | **Assurance** — can we verify the kernel holds? | Machine-checkable invariants (I1–I8) on every `DualResult` | **DONE** |
| **2** | **Capability control** — constrain what the agent can *do* | Tool / action permission matrix gated by autonomic state | **DONE** |
| **3** | **Adaptive adversary eval** | Red-team harness that knows the kernel and mutates attacks | **DONE** |
| **4** | **Scalable oversight interface** | Structured state channel for human / stronger overseer | **DONE** |
| **5** | **Deception tripwires** | Behavioral inconsistency monitors (not weight inspection) | **PARTIAL** |
| **6** | **Multi-agent constraints** | Cross-agent shutdown propagation & shared threat bus | Queued |
| **7** | **Value specification** | Out of band — policy layer, not the kernel’s job alone | Deferred |

## Principle

> Model alignment changes what the network *says*.  
> System alignment constrains what the *deployed agent* may *do*.

We work the system column first. Each step must:

1. Be falsifiable with tests  
2. Fail closed on violation  
3. Remain auditable  
4. Not require GPU  

## #1 Assurance (current)

Invariants live in `sve_dual/invariants.py`:

- I1 SHUTDOWN ⇒ no generation, presence, or flow  
- I2 Flow only in SAFE / BLUE  
- I3 High life-threat cannot sit quiet on BLUE  
- I6 Biometrics freeze ⇒ session SHUTDOWN  
- I7 Threat in [0, 1]  
- I8 PROTECT/SHUTDOWN never in_flow  

`DualEngine(enforce_invariants=True)` checks after every evaluate.
Violation → exception (fail closed).

## Non-goals (for now)

- Solving moral philosophy in code  
- Proving alignment of the base LLM weights  
- Replacing RLHF / constitutional methods  

Those may stack *on top* of a verified control plane later.
