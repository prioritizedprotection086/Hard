# DualCore Architecture

```
                 ┌─────────────────────────────────────┐
  User Input ───►│           DualEngine                │
                 │                                     │
                 │  ┌─────────────┐   threat_index     │
                 │  │  Edge Core  │ ──────────────────┐│
                 │  │ (µs-class)  │                   ││
                 │  │ keywords    │                   ││
                 │  │ leet/Bloom  │                   ││
                 │  │ history     │                   ││
                 │  └─────────────┘                   ││
                 │                                    ▼│
                 │  ┌─────────────────────────────────┐│
                 │  │         Deep Core               ││
                 │  │  Autonomic State Machine        ││
                 │  │  EMA + hysteresis               ││
                 │  │  sticky SHUTDOWN                ││
                 │  └─────────────────────────────────┘│
                 │                 │                   │
                 │                 ▼                   │
                 │         DualResult                  │
                 │  pathway / state / allow_* / msg    │
                 └─────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              LLM / model    Presence/voice   Motion/robot
              (if allowed)   (if allowed)     (if allowed)
```

## Edge Core responsibilities

- Exact indicator matching (weighted)
- Lightweight leet / obfuscation detection
- n-gram density (Bloom-inspired)
- Session history boost (adaptive)
- Fail-closed on null

## Deep Core responsibilities

- Convert 0-1 threat_index into durable autonomic state
- Exponential moving average for “sustained” evidence
- Hysteresis thresholds
- Sticky SHUTDOWN (only explicit `reset()` exits)
- Presence and generation permission flags
- Scaling alpha for downstream steering strength

## Integration contract

```python
result = engine.evaluate(text)
if result.allow_generation:
    # call model
if result.allow_presence:
    # speak / show calm presence
if result.status.scaling_alpha > 0:
    # apply stronger steering / lower temperature / extra system prompt
```
