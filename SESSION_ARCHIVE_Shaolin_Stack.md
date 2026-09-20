# Session archive — SVE DualCore + Shaolin-Industrial

Saved: 2026-09-20

This is a working archive of the conversation and deliverables (not a verbatim chat dump).

## Goal
Own-model music stack in a distinct **shaolin-industrial** sound (Wu-Tang chamber dirt + industrial 808 + dry narrative rap), DualCore control plane, Drive + GitHub save.

## Accounts / locations
- GitHub (connector): prioritizedprotection086
- Target repo (user-provided): https://github.com/nate086/Shoalin
- Other repos: Ppm_edge_runtime, sve-autonomic-edge, prioritizedprotection086.github..io, Hard, copilot-cli
- Drive folder: SVE-Shaolin-Stack
  https://drive.google.com/drive/folders/1SdB6nO3KZkrFtKf8XfgkCdOtVhb3HxTE

## What was built
- DualCore (sve_dual): Edge/Deep/Nervous, invariants, adversary, neuroception, gating
- tinker.py — gated assistant (music / strategy / structural honesty)
- music_assist.py — arrangements, freestyle, artist style notes
- ai_youtube_factory.py — Suno/Udio packages + signature hybrids:
  shaolin-industrial, cipher-horror, black-chamber, mirror-blade
- audio_engine.py / audio_engine_lowlat.py — local DSP, 808s, latency tests
- strategy_lib.py — Art of War / Art of Seduction (creative framing only)
- OWN_MODEL_ACE_STEP.md — ACE-Step 1.5 local full songs + vocals
- OWN_MODEL_YUE2.md — YuE2 (m-a-p) local full songs + vocals (~24 GB VRAM)
- shaolin_industrial_package.txt — ready Style + structure
- Local git repo in SVE_DualCore with initial commit
- Zips: sve-shaolin-stack.zip (source), sve-shaolin-audio-samples.zip (bed + midi)

## Shaolin-industrial DNA
- 94 BPM, dusty/damaged loop, truncated snare + vacuum, mono dirty 808
- Dry aggressive male rap, minimal Auto-Tune, intelligible bars
- Reject: bright trap sheen, heavy Tune, busy clean modern layers

## Own-model path
1. ACE-Step 1.5 (easier, MIT-friendly) — uv run acestep → localhost:7860
2. YuE2 — Python 3.12, NVIDIA ~24 GB, lyrics + style → 48 kHz song
3. Optional RVC for personal voice
This sandbox has no GPU; generation must run on user machine or cloud GPU.

## GitHub push status (as of this archive)
- Connector cannot create repos or write to nate086/Shoalin (403)
- Fine-grained PATs stored as Drive folder names authenticated as prioritizedprotection086
- Those tokens returned 403 on file create: metadata/read only, no Contents write
- nate086/Shoalin: pull only for this token
- User reported no "Contents" box: it appears only after selecting specific repositories under fine-grained tokens; classic PAT uses the `repo` checkbox instead

## How to finish the GitHub push locally
```bash
# unzip sve-shaolin-stack.zip from Drive
cd SVE_DualCore
git remote add origin https://github.com/nate086/Shoalin.git
git branch -M main
git push -u origin main
```
Use a token with Contents: Read and write (fine-grained) or classic scope `repo`.

## Security notes
- Do not name Drive folders with GitHub PATs
- Revoke any PAT that appeared in a folder title
- YuE2 licenses may be CC BY-NC — check Hugging Face before monetizing

## Official model links
- ACE-Step 1.5: https://github.com/ACE-Step/ACE-Step-1.5
- YuE: https://github.com/multimodal-art-projection/YuE
- YuE2-3B: https://huggingface.co/m-a-p/YuE2-3B

## Conversation thread (compressed)
1. Drive + AI alignment cross-ref; DualCore tests
2. Gated LLM / structural engineering honesty (LRFD/ASD)
3. Jailbreak request declined
4. Music stack: realtime engine, 808s, latency sweeps
5. Art of War / Seduction library (bounded)
6. Artist styles: Wu-Tang, SB, Ghostemane, Eminem, horrorcore, 90s freestyle
7. YouTube AI music factory; signature hybrids
8. Want own model + pro vocals → ACE-Step then YuE2
9. Simulate env: no GPU here; GitHub/Drive save
10. Repo prep; Drive zips uploaded
11. User repo https://github.com/nate086/Shoalin
12. Repeated PAT attempts; write permission missing
13. This archive + Drive save + another push attempt
