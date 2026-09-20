# Your Own Model — ACE-Step 1.5 + Shaolin-Industrial

**Choice:** ACE-Step (easier setup, full songs + vocals, MIT-friendly commercial use)

## Hardware guide

| VRAM | What to run |
|------|-------------|
| ≤6 GB | 2B turbo DiT only (lighter) |
| 8–16 GB | 2B turbo/sft + small LM — good default |
| 16–24 GB | XL options if you want max quality |
| No GPU | CPU works but slow; or rent cloud GPU |

Disk: ~10 GB for core models.

---

## Install (your machine)

```bash
# 1. Package manager
curl -LsSf https://astral.sh/uv/install.sh | sh          # Mac/Linux
# Windows PowerShell:
# irm https://astral.sh/uv/install.ps1 | iex

# 2. Clone + install
git clone https://github.com/ACE-Step/ACE-Step-1.5.git
cd ACE-Step-1.5
uv sync

# 3. Launch Gradio UI (models download on first run)
uv run acestep
```

Open **http://localhost:7860**

Windows portable package also available from ACE-Step docs if you prefer one-click.

API server (optional, for DualCore later):
```bash
uv run acestep-api
# → http://localhost:8001
```

---

## First shaolin-industrial generate

**Style / tags field** (paste):
```
experimental hip-hop, industrial boom bap, dark sample collage, underground narrative rap, cinematic menace, cold focus, martial, nocturnal, unpolished power, detuned dusty soul or film-score loop, truncated snare, off-grid kick, distorted mono 808 under the sample, sparse industrial hits, vinyl and tape grit, sudden silence, dry aggressive male rap, complex internals, calm-to-bark dynamics, minimal Auto-Tune, group ad-libs only on hooks, intelligible storytelling, 94 BPM, NOT clean modern trap, NOT generic boom bap, Shaolin chamber dirt plus industrial low-end, vacuum after snares, one damaged loop carries the track, no bright pop sheen
```

**Lyrics field** (structure):
```
[Intro]
[Verse]
(your original bars)
[Hook]
(your original hook)
[Verse]
[Hook]
[Bridge]
[Verse]
[Hook]
[Outro]
```

**Reject if:** bright trap sheen, heavy melodic Auto-Tune, busy clean modern layers, buried vocal.

**Keep if:** dusty/damaged loop, truncated snare air, mono dirty low end, dry intelligible bars, cold martial mood.

---

## Optional: your voice (pro identity)

1. Record 10–30 min clean dry vocals (rap/sing).
2. Train RVC / Applio on that set.
3. Convert ACE-Step lead vocal → your RVC model.
4. Mix: your voice + ACE instrumental (or full track after conversion).

---

## Wire to DualCore later

Once ACE-Step API is running on :8001, we can point the factory at localhost so:
`shaolin-industrial package` → local generate → WAV in your folder.

---

## Repo

https://github.com/ACE-Step/ACE-Step-1.5
