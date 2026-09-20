#!/usr/bin/env python3
"""
AI YouTube Music Factory
========================
How the tracks flooding YouTube are actually made — and a prompt engine
so you can aim at the same output.

Pipeline used by high-volume AI music channels (2025–2026):
  1. Concept + lyrics (human or LLM)
  2. Generate full song in Suno (vocals) or Udio (fidelity)
  3. Iterate 5–20 variants; keep best
  4. Optional: stems → DAW polish → AI master (LANDR / eMastered)
  5. Cover art (Midjourney / Flux) + visualizer / lyric video
  6. Upload YouTube (+ DistroKid for Spotify etc. if desired)
  7. Paid plan required for commercial / monetized use

This module builds *platform-ready prompts* from our style library
(Wu-Tang, trap, horrorcore, 90s freestyle, etc.) so you paste into
Suno/Udio and get closer to the sound you want on the first tries.
"""

from __future__ import annotations
from typing import Dict, List, Optional
import random

# ---------------------------------------------------------------------------
# Style DNA — maps our library → Suno/Udio prompt language
# ---------------------------------------------------------------------------

STYLE_DNA: Dict[str, Dict] = {
    "wu-tang": {
        "genre_tags": "boom bap, dusty hip-hop, 1990s East Coast, sample-based, gritty",
        "mood": "dark, cinematic, martial, raw, underground",
        "instruments": "dusty soul sample loop, hard kick, cracking snare, sparse hats, mono sub bass, vinyl crackle",
        "vocal": "raw male rap vocals, multiple MCs trading verses, minimal Auto-Tune, dry presence",
        "bpm": "92",
        "structure": "[Intro]\n[Verse]\n[Hook]\n[Verse]\n[Hook]\n[Verse]\n[Hook]\n[Outro]",
        "extra": "kung-fu atmosphere, chamber music grit, off-kilter swing, lo-fi 12-bit character",
    },
    "90s freestyle": {
        "genre_tags": "1990s hip-hop, battle rap, cipher freestyle, high energy boom bap",
        "mood": "aggressive, urgent, competitive, live",
        "instruments": "hard kick and snare, busy hats optional, one strong loop, DJ scratches",
        "vocal": "raw male rap, multisyllabic, punchline dense, minimal effects, board-mic energy",
        "bpm": "98",
        "structure": "[Intro]\n[Verse]\n[Verse]\n[Break]\n[Verse]\n[Outro]",
        "extra": "cipher energy, no long intro, leave space for punchlines",
    },
    "suicideboys": {
        "genre_tags": "dark trap, underground trap, Memphis influenced, cloud rap",
        "mood": "bleak, depressive, aggressive, nocturnal",
        "instruments": "distorted 808, triple-time hi-hats, hard clap, chopped horror sample, industrial noise",
        "vocal": "male rap with Auto-Tune, dual voices, reverb-heavy ad-libs, half-sung hooks",
        "bpm": "145",
        "structure": "[Intro]\n[Verse]\n[Hook]\n[Verse]\n[Hook]\n[Bridge]\n[Hook]\n[Outro]",
        "extra": "lo-fi grit meets modern sub, sudden drops, oppressive atmosphere",
    },
    "ghostemane": {
        "genre_tags": "trap metal, industrial hip-hop, blackened trap",
        "mood": "aggressive, dark, chaotic, intense",
        "instruments": "distorted bass, industrial drums, harsh synth or guitar, noise layers",
        "vocal": "rap verses switching to harsh screams, aggressive compression",
        "bpm": "150",
        "structure": "[Intro]\n[Verse]\n[Build]\n[Drop]\n[Verse]\n[Drop]\n[Outro]",
        "extra": "short song length, high contrast whisper vs full assault",
    },
    "eminem": {
        "genre_tags": "hip-hop, storytelling rap, battle rap, 2000s classic hip-hop",
        "mood": "intense, sharp, narrative, dynamic",
        "instruments": "clean hard drums, sparse piano or guitar motif, deep simple bass",
        "vocal": "precise male rap, complex internal rhymes, character voice switches, dry and present",
        "bpm": "95",
        "structure": "[Intro]\n[Verse]\n[Hook]\n[Verse]\n[Hook]\n[Bridge]\n[Verse]\n[Hook]\n[Outro]",
        "extra": "vocal clarity priority, beat leaves space for words, optional beat switch",
    },
    "horrorcore": {
        "genre_tags": "horrorcore, West Coast hardcore hip-hop, dark narrative rap",
        "mood": "menacing, cinematic, grim, storytelling",
        "instruments": "funky dark bass, hard drums, minor key stabs, eerie pads",
        "vocal": "calm-menacing or aggressive-clear male rap, minimal Auto-Tune",
        "bpm": "98",
        "structure": "[Intro]\n[Verse]\n[Hook]\n[Verse]\n[Hook]\n[Bridge]\n[Hook]\n[Outro]",
        "extra": "narrative first, intelligible vocals, horror atmosphere without drowning the story",
    },
    "trap": {
        "genre_tags": "modern trap, melodic trap, 808 heavy",
        "mood": "dark, energetic, street, hypnotic",
        "instruments": "808 slides, rolling hi-hats, crisp snare, dark pluck melody, atmospheric pad",
        "vocal": "melodic male rap, Auto-Tune, ad-libs, hook-focused",
        "bpm": "142",
        "structure": "[Intro]\n[Verse]\n[Hook]\n[Verse]\n[Hook]\n[Bridge]\n[Hook]\n[Outro]",
        "extra": "hook first energy, mono low end, space for vocal",
    },
    "lofi": {
        "genre_tags": "lo-fi hip-hop, chillhop, jazzy beats",
        "mood": "relaxed, nostalgic, warm, late night",
        "instruments": "dusty Rhodes or piano, soft kick, swung hats, vinyl crackle, muted bass",
        "vocal": "optional soft vocal chops, no lead vocal, or whispered",
        "bpm": "82",
        "structure": "[Intro]\n[A]\n[B]\n[A]\n[Outro]",
        "extra": "imperfect timing, warm tape saturation, headroom, study/background friendly",
    },
    "pop": {
        "genre_tags": "contemporary pop, radio pop, polished",
        "mood": "uplifting, emotional, catchy",
        "instruments": "punchy drums, synths, bass locked to kick, wide pads",
        "vocal": "polished male or female lead, doubles on chorus, clear diction",
        "bpm": "118",
        "structure": "[Intro]\n[Verse]\n[Pre-Chorus]\n[Chorus]\n[Verse]\n[Pre-Chorus]\n[Chorus]\n[Bridge]\n[Chorus]\n[Outro]",
        "extra": "chorus as arrival, pre-chorus tension, signature motif",
    },
    # SIGNATURE HYBRIDS — your lane, not generic YouTube AI
    # DNA: Wu-Tang + $uicideboy$ + Ghostemane + Eminem + 90s freestyle + horrorcore
    "shaolin-industrial": {
        "genre_tags": "experimental hip-hop, industrial boom bap, dark sample collage, underground narrative rap",
        "mood": "cinematic menace, cold focus, martial, nocturnal, unpolished power",
        "instruments": "detuned dusty soul or film-score loop, truncated snare, off-grid kick, distorted mono 808 under the sample, sparse industrial hits, vinyl and tape grit, sudden silence",
        "vocal": "dry aggressive male rap, complex internals, calm-to-bark dynamics, minimal Auto-Tune, group ad-libs only on hooks, intelligible storytelling",
        "bpm": "94",
        "structure": "[Intro]\n[Verse]\n[Hook]\n[Verse]\n[Hook]\n[Bridge]\n[Verse]\n[Hook]\n[Outro]",
        "extra": "NOT clean modern trap, NOT generic boom bap; Shaolin chamber dirt plus industrial low-end; vacuum after snares; one damaged loop carries the track; no bright pop sheen",
    },
    "cipher-horror": {
        "genre_tags": "horrorcore boom bap, 90s freestyle energy, dark West Coast narrative, underground hardcore hip-hop",
        "mood": "menacing, urgent, storytelling, live-cipher intensity",
        "instruments": "hard dusty drums, funk-dark bass, minor horror stabs, one loop bed, occasional scratch, room noise",
        "vocal": "clear aggressive or calm-menacing male rap, multisyllabic runs, punchline stacks, almost no Auto-Tune, upfront mic presence",
        "bpm": "96",
        "structure": "[Intro]\n[Verse]\n[Verse]\n[Hook]\n[Verse]\n[Hook]\n[Outro]",
        "extra": "cipher-first; stable beat so bars land; horror atmosphere without drowning the narrative; raw board energy not studio gloss",
    },
    "black-chamber": {
        "genre_tags": "dark experimental hip-hop, chamber trap, industrial narrative, lo-fi grit with modern sub",
        "mood": "bleak, focused, oppressive then sparse, late-night",
        "instruments": "pitched-down soul or horror sample, long distorted 808, triple hats only in bursts, hard clap, noise beds, abrupt filter cuts",
        "vocal": "male rap dual texture dry verse wet ad-libs, half-sung grim hook, controlled Auto-Tune not melodic pop",
        "bpm": "138",
        "structure": "[Intro]\n[Verse]\n[Hook]\n[Verse]\n[Bridge]\n[Hook]\n[Outro]",
        "extra": "SB bleakness plus Wu sample world plus Ghostemane contrast; avoid bright leads and happy loops; silence and sudden drops as arrangement",
    },
    "mirror-blade": {
        "genre_tags": "storytelling hip-hop, sharp boom bap, dynamic underground rap",
        "mood": "intense, precise, psychological, switching heat",
        "instruments": "clean-but-hard drums, sparse piano or detuned motif, deep simple bass, wide empty space around the vocal",
        "vocal": "precise male rap, internal rhyme density, persona or tone switches, whisper-to-bark, dry and present, no heavy effects",
        "bpm": "93",
        "structure": "[Intro]\n[Verse]\n[Hook]\n[Verse]\n[Bridge]\n[Verse]\n[Hook]\n[Outro]",
        "extra": "Eminem clarity plus Wu atmosphere plus freestyle urgency; arrange for the words first; optional late beat switch; never bury the vocal",
    },
}


def build_suno_prompt(
    style: str = "trap",
    custom_mood: Optional[str] = None,
    custom_bpm: Optional[str] = None,
    instrumental: bool = False,
    era_note: Optional[str] = None,
) -> str:
    """Comma-tag style prompt optimized for Suno (genre-first)."""
    key = style.lower().strip()
    for k in STYLE_DNA:
        if k in key or key in k:
            key = k
            break
    else:
        key = "trap"
    d = STYLE_DNA[key]
    mood = custom_mood or d["mood"]
    bpm = custom_bpm or d["bpm"]
    vocal = "no vocals, instrumental" if instrumental else d["vocal"]
    parts = [
        d["genre_tags"],
        mood,
        d["instruments"],
        vocal,
        f"{bpm} BPM",
        d["extra"],
        "studio quality",
    ]
    if era_note:
        parts.insert(1, era_note)
    return ", ".join(parts)


def build_udio_prompt(style: str = "trap", scene: Optional[str] = None) -> str:
    """Natural-language scene prompt (Udio often prefers this)."""
    key = style.lower().strip()
    for k in STYLE_DNA:
        if k in key or key in k:
            key = k
            break
    else:
        key = "trap"
    d = STYLE_DNA[key]
    if scene:
        return scene
    return (
        f"A {d['mood']} {d['genre_tags']} track at {d['bpm']} BPM, "
        f"featuring {d['instruments']}, with {d['vocal']}. "
        f"{d['extra']}."
    )


def build_lyrics_scaffold(style: str = "trap", theme: str = "night drive") -> str:
    """Section-tagged lyric scaffold for Suno Custom mode."""
    key = style.lower().strip()
    dna = STYLE_DNA.get(key, STYLE_DNA["trap"])
    structure = dna["structure"]
    lines = [
        f"(Theme: {theme} | Style: {key})",
        "",
        structure.replace("[Intro]", "[Intro]\n(instrumental or short hook line)"),
    ]
    # Add placeholder bars for verses
    scaffold = structure
    for tag in ("[Verse]", "[Hook]", "[Chorus]", "[Bridge]"):
        if tag in scaffold:
            scaffold = scaffold.replace(
                tag,
                f"{tag}\n(write 4–8 lines — original bars only)",
                1,
            )
    return f"(Theme: {theme})\n\n{scaffold}"


def full_package(
    style: str = "wu-tang",
    theme: str = "chamber strategy",
    instrumental: bool = False,
) -> str:
    """Complete brief: Suno prompt + Udio prompt + lyric scaffold + workflow."""
    suno = build_suno_prompt(style, instrumental=instrumental)
    udio = build_udio_prompt(style)
    lyrics = build_lyrics_scaffold(style, theme)
    dna = STYLE_DNA.get(style if style in STYLE_DNA else "trap", STYLE_DNA["trap"])

    return f"""
═══════════════════════════════════════════════════════════
AI YOUTUBE MUSIC PACKAGE — {style.upper()}
═══════════════════════════════════════════════════════════

HOW THE YOUTUBE AI ARTISTS ACTUALLY DO IT
  1. Write or generate lyrics + clear style brief
  2. Paste into Suno (Custom mode) or Udio
  3. Generate 5–15 versions; keep top 1–2
  4. Optional: export stems → light DAW fix → AI master
  5. Cover art + visualizer / lyric video
  6. Upload (paid plan = commercial rights for monetization)
  7. Channels that last add human craft (thumbnails, titles, curation)

───────────────────────────────────────────────────────────
SUNO STYLE PROMPT (paste into Style field)
───────────────────────────────────────────────────────────
{suno}

───────────────────────────────────────────────────────────
UDIO PROMPT (natural language)
───────────────────────────────────────────────────────────
{udio}

───────────────────────────────────────────────────────────
LYRIC / STRUCTURE SCAFFOLD (Suno Lyrics field)
───────────────────────────────────────────────────────────
{lyrics}

───────────────────────────────────────────────────────────
SUGGESTED STRUCTURE TAGS
───────────────────────────────────────────────────────────
{dna['structure']}

───────────────────────────────────────────────────────────
POST-GENERATE CHECKLIST
───────────────────────────────────────────────────────────
  [ ] Pick best take (hook + vocal clarity)
  [ ] If muddy: regenerate with 'clear vocals, tight low end'
  [ ] Optional stem split → balance 808/kick
  [ ] Master to ~-9 to -7 LUFS for YouTube music
  [ ] Visual: waveform / AI video / lyric cards
  [ ] Disclose synthetic content if required by platform
  [ ] Paid tier before monetizing

Original lyrics and performance intent only.
""".strip()


def list_styles() -> str:
    return "Available style packages:\n  " + "\n  ".join(f"• {k}" for k in STYLE_DNA)


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if not args or args[0] in ("list", "styles"):
        print(list_styles())
    elif args[0] == "udio":
        print(build_udio_prompt(args[1] if len(args) > 1 else "trap"))
    else:
        style = args[0]
        theme = " ".join(args[1:]) if len(args) > 1 else "night run"
        print(full_package(style, theme))
