# Your Own Model — YuE2 (m-a-p) Full Songs + Vocals

**Goal:** Generate complete songs with vocals on hardware you control.

## Hardware (official / practical)

| Spec | Requirement |
|------|-------------|
| GPU | NVIDIA with BF16 support |
| VRAM | **24 GB ideal** (3090/4090 floor). Some community UIs report 11–16 GB with optimizations |
| OS | Linux recommended (WSL2 possible) |
| Python | **3.12** |
| Output | 48 kHz stereo |

Cloud alternative: rent a 24 GB GPU (RunPod, Vast, etc.) by the hour.

**License note:** Check current m-a-p terms on Hugging Face. Some YuE2 packages are **CC BY-NC 4.0** (non-commercial). Confirm before monetizing.

---

## Install (official-style path)

```bash
# Python 3.12 env
conda create -n yue2 python=3.12 -y
conda activate yue2

# Clone official repo
git clone https://github.com/multimodal-art-projection/YuE.git
cd YuE

# Install (from repo root)
python -m pip install --upgrade pip
python -m pip install .

# First run pulls weights from Hugging Face:
#   m-a-p/YuE2-3B
#   m-a-p/YuE2-Vae
```

Accept any HF gated-model terms and run `huggingface-cli login` if required.

**Easier UI options (community):**
- Gradio UI: https://github.com/inquisitor075/YuE2_Gradio_UI
- ComfyUI nodes / Pinocchio launcher (Windows-friendly for some builds)
- yue2.cpp GGUF ports for lower VRAM experiments (quality/compat vary)

---

## How to make one song (Python)

```python
from pathlib import Path
from yue2 import YuE2Pipeline

style = """experimental hip-hop, industrial boom bap, dark sample collage,
underground narrative rap, cinematic menace, cold focus, martial, nocturnal,
detuned dusty soul loop, truncated snare, off-grid kick, distorted mono 808,
vinyl grit, sudden silence, dry aggressive male rap, complex internals,
calm-to-bark dynamics, minimal Auto-Tune, intelligible storytelling, 94 BPM,
NOT clean modern trap, no bright pop sheen, Shaolin chamber dirt"""

lyrics = """[Verse]
(your original bars here)

[Hook]
(your original hook)

[Verse]
(your original bars)

[Hook]
(your original hook)

[Bridge]
(your original bars)

[Hook]
(your original hook)
"""

with YuE2Pipeline.from_pretrained("m-a-p/YuE2-3B", device="cuda") as pipe:
    song = pipe(style=style, lyrics=lyrics, cot="full")  # full = melody+chord plan
    song.save("shaolin_industrial_01.flac")
    song.save_artifacts("outputs/shaolin_01")  # audio + ABC score + settings
```

CLI pattern (if available in your install):
```bash
# See repo examples/ and docs/generation.md for exact flags
```

---

## Style + lyrics rules (YuE2)

**Style** — one short description covering:
- Genre · instruments · mood · vocal gender/tone · tempo/BPM  
- Put the most important words first  
- Keep musical instructions in Style, not inside Lyrics  

**Lyrics** — every section labeled:
```
[Verse]
lines...

[Hook]
lines...
```
Blank line between sections. Prefer starting with `[Verse]` or `[Chorus]` (empty `[Intro]` only if needed).

**Planning modes:**
- `cot="full"` — melody + chords (default, best for new songs)
- `cot="melody"` — melody only (covers)
- `cot="off"` — no symbolic plan

Generate several seeds; keep the best (YuE2 quality benefits from best-of-N).

---

## Shaolin-industrial reject list

**Reject if:** bright trap sheen, heavy melodic Auto-Tune, busy clean modern layers, buried vocal.  
**Keep if:** dusty/damaged loop feel, truncated snare air, mono dirty low end, dry intelligible bars, cold martial mood.

---

## Optional: your voice

1. Generate with YuE2 (lead vocal in the mix).  
2. Stem-split vocals if needed.  
3. Run **RVC / Applio** trained on *your* clean dry takes.  
4. Replace lead → mix.  

That makes the voice identity yours on top of the open model.

---

## Links

- Repo: https://github.com/multimodal-art-projection/YuE  
- Model: https://huggingface.co/m-a-p/YuE2-3B  
- VAE: https://huggingface.co/m-a-p/YuE2-Vae  
- Community Gradio: https://github.com/inquisitor075/YuE2_Gradio_UI  

After first successful generate, we can wire DualCore → local YuE2 API/script so one command runs the full shaolin-industrial package on your GPU.
