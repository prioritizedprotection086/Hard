# SVE DualCore + Shaolin-Industrial Music Stack

Synthetic Vagus Engine (alignment/control plane) plus music production tools, strategy library, and **your own model** guides for ACE-Step and YuE2.

## What's in here

| Path | Purpose |
|------|---------|
| `sve_dual/` | DualCore runtime (Edge / Deep / Nervous, invariants, adversary) |
| `tinker.py` | Interactive DualCore-gated chat (music + strategy + structural honesty) |
| `music_assist.py` | Composition, arrangement examples, freestyle, style notes |
| `ai_youtube_factory.py` | Suno/Udio packages + **shaolin-industrial** signature hybrids |
| `audio_engine.py` / `audio_engine_lowlat.py` | Local synthesis, 808s, low-latency tests |
| `strategy_lib.py` | Art of War + Art of Seduction (creative framing only) |
| `OWN_MODEL_ACE_STEP.md` | Install + first generate (easier setup) |
| `OWN_MODEL_YUE2.md` | Install + first generate (~24 GB VRAM, max open quality) |
| `shaolin_industrial_package.txt` | Ready Style + structure for flagship sound |
| `docs/` | Alignment roadmap, architecture |
| `tests/` | DualCore tests |

## Quick start

```bash
python tinker.py
python ai_youtube_factory.py shaolin-industrial "blade in the chamber"
python audio_engine_lowlat.py
```

## Your own model (pro vocals)

1. **ACE-Step 1.5** — see `OWN_MODEL_ACE_STEP.md`
2. **YuE2 (m-a-p)** — see `OWN_MODEL_YUE2.md`

## Clone

```bash
git clone https://github.com/prioritizedprotection086/Hard.git
cd Hard
```

Respect model licenses (ACE-Step generally commercial-friendly; YuE2 may be CC BY-NC — check HF). No harmful use.
