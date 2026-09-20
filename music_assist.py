#!/usr/bin/env python3
"""
SVE DualCore Music Production Assistant
=======================================
Composition • Sample Arrangement • Auto-Tuner guidance • Effects Processor
Realtime Freestyle ideas • Artist Voice Mimicking notes • Music Creator

Integrates with DualEngine for gated, safe creative use.
Generates MIDI sketches, arrangement maps, production recipes, and freestyle prompts.
"""

from __future__ import annotations
import os
import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path

try:
    from midiutil import MIDIFile
    HAS_MIDI = True
except ImportError:
    HAS_MIDI = False

# ---------------------------------------------------------------------------
# Musical knowledge base
# ---------------------------------------------------------------------------

KEYS = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
MODES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
}

CHORD_QUALITIES = {
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "7": [0, 4, 7, 10],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "add9": [0, 4, 7, 14],
}

PROGRESSIONS = {
    "pop": ["I", "V", "vi", "IV"],
    "sad": ["vi", "IV", "I", "V"],
    "jazz": ["ii", "V", "I", "vi"],
    "rock": ["I", "bVII", "IV", "I"],
    "trap": ["i", "VI", "III", "VII"],
    "lofi": ["ii7", "V7", "Imaj7", "vi7"],
    "edm": ["i", "VI", "III", "VII"],
    "rnb": ["Imaj7", "iii7", "vi7", "II7"],
}

ROMAN_TO_DEGREE = {
    "I": 0, "II": 2, "III": 4, "IV": 5, "V": 7, "VI": 9, "VII": 11,
    "i": 0, "ii": 2, "iii": 3, "iv": 5, "v": 7, "vi": 8, "vii": 10,
    "bVII": 10, "bIII": 3, "bVI": 8,
    "ii7": 2, "V7": 7, "Imaj7": 0, "vi7": 9, "iii7": 4, "II7": 2,
}

GENRES = [
    "hip-hop", "trap", "r&b", "pop", "lofi", "edm", "house", "techno",
    "rock", "indie", "jazz", "soul", "afrobeats", "reggaeton", "drill",
    "ambient", "cinematic", "phonk", "hyperpop"
]

EFFECTS_LIBRARY = {
    "reverb": "Space & depth. Plate / Hall / Room / Spring. Pre-delay 20-80ms, decay 1.2-3.5s for vocals.",
    "delay": "Rhythmic echo. 1/8 or 1/4 note synced, feedback 25-45%, low-pass on repeats.",
    "compressor": "Glue & punch. Ratio 3:1–6:1, attack 5-30ms, release 50-150ms. Parallel for drums.",
    "eq": "Surgical + tone. High-pass vocals ~80-120Hz, presence boost 3-5kHz, air 10-12kHz.",
    "saturation": "Warmth / harmonics. Tape or tube style, drive 10-25%, mix 30-60%.",
    "auto-tune": "Pitch correction. Retune speed 0-20ms (hard) to 40-100ms (natural). Humanize 20-40%.",
    "chorus": "Width. Rate 0.5-1.5Hz, depth 20-40%, mix 25%.",
    "distortion": "Aggression. Soft clip or amp sim, drive to taste, post-EQ harshness.",
    "sidechain": "Pumping. Duck pad/bass against kick, ratio 4:1+, fast attack, medium release.",
    "stereo_imager": "Width control. Keep low-end mono (<120Hz), widen highs carefully.",
}

ARRANGEMENT_SECTIONS = ["Intro", "Verse", "Pre-Chorus", "Chorus", "Post-Chorus", "Bridge", "Drop", "Outro", "Breakdown"]


@dataclass
class SongSketch:
    title: str
    key: str
    mode: str
    bpm: int
    genre: str
    progression: List[str]
    structure: List[str]
    energy_map: List[str]
    notes: str = ""


def note_name_to_midi(note: str, octave: int = 4) -> int:
    """C4 = 60"""
    base = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
            "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
            "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
    return 12 * (octave + 1) + base.get(note.upper().replace("♯", "#"), 0)


def build_chord(root_midi: int, quality: str = "maj") -> List[int]:
    intervals = CHORD_QUALITIES.get(quality, CHORD_QUALITIES["maj"])
    return [root_midi + i for i in intervals]


def roman_to_chord(roman: str, key_root: int, mode: str = "major") -> Tuple[int, str]:
    """Return (root_midi, quality_guess)"""
    degree = ROMAN_TO_DEGREE.get(roman, 0)
    root = key_root + degree
    if roman[0].islower() or "min" in roman.lower() or roman in ("ii", "iii", "vi", "ii7", "vi7", "iii7"):
        qual = "min7" if "7" in roman else "min"
    elif "maj7" in roman:
        qual = "maj7"
    elif "7" in roman:
        qual = "7"
    else:
        qual = "maj"
    return root, qual


# ---------------------------------------------------------------------------
# Core generators
# ---------------------------------------------------------------------------

def compose_sketch(
    genre: str = "pop",
    key: Optional[str] = None,
    bpm: Optional[int] = None,
    mood: str = "uplifting",
) -> SongSketch:
    genre = genre.lower()
    key = key or random.choice(KEYS)
    mode = "minor" if mood in ("sad", "dark", "melancholy", "trap", "drill") else "major"
    if genre in ("trap", "drill", "phonk", "lofi"):
        mode = "minor"

    bpm_map = {
        "trap": (130, 160), "drill": (135, 150), "hip-hop": (85, 100),
        "r&b": (70, 95), "pop": (100, 128), "edm": (120, 140),
        "house": (120, 128), "lofi": (70, 90), "rock": (110, 140),
        "jazz": (90, 140), "ambient": (60, 90),
    }
    lo, hi = bpm_map.get(genre, (90, 120))
    bpm = bpm or random.randint(lo, hi)

    prog_key = genre if genre in PROGRESSIONS else random.choice(list(PROGRESSIONS))
    if mood == "sad":
        prog_key = "sad"
    progression = PROGRESSIONS.get(prog_key, PROGRESSIONS["pop"])

    # Structure templates by genre
    if genre in ("edm", "house", "techno"):
        structure = ["Intro", "Build", "Drop", "Break", "Build", "Drop", "Outro"]
    elif genre in ("trap", "drill", "hip-hop"):
        structure = ["Intro", "Verse", "Chorus", "Verse", "Chorus", "Bridge", "Chorus", "Outro"]
    elif genre == "lofi":
        structure = ["Intro", "A", "B", "A", "Outro"]
    else:
        structure = ["Intro", "Verse", "Pre-Chorus", "Chorus", "Verse", "Pre-Chorus", "Chorus", "Bridge", "Chorus", "Outro"]

    energy = []
    for sec in structure:
        if sec in ("Drop", "Chorus"):
            energy.append("HIGH")
        elif sec in ("Verse", "A", "Break"):
            energy.append("MID")
        elif sec in ("Intro", "Outro", "Breakdown"):
            energy.append("LOW")
        else:
            energy.append("BUILD")

    title = f"{genre.title()} Sketch in {key} {mode}"
    notes = (
        f"Key centre: {key} {mode}. Progression: {' – '.join(progression)}. "
        f"Suggested pocket: focus on groove first, then melody. "
        f"Leave space for vocal or lead."
    )

    return SongSketch(
        title=title,
        key=key,
        mode=mode,
        bpm=bpm,
        genre=genre,
        progression=progression,
        structure=structure,
        energy_map=energy,
        notes=notes,
    )


def arrangement_map(sketch: SongSketch) -> str:
    lines = [
        f"═══ ARRANGEMENT MAP ═══",
        f"Title : {sketch.title}",
        f"Key   : {sketch.key} {sketch.mode}   |   BPM: {sketch.bpm}   |   Genre: {sketch.genre}",
        f"Prog  : {' → '.join(sketch.progression)}",
        "",
        "Section          Bars   Energy   Focus",
        "─" * 48,
    ]
    bar = 1
    for sec, eng in zip(sketch.structure, sketch.energy_map):
        length = 8 if sec in ("Chorus", "Drop") else 4 if sec in ("Intro", "Outro") else 8
        lines.append(f"{sec:<16} {bar:>3}-{bar+length-1:<3}  {eng:<7}  {focus_for(sec)}")
        bar += length
    lines.append("")
    lines.append(sketch.notes)
    return "\n".join(lines)


def focus_for(section: str) -> str:
    return {
        "Intro": "texture / motif",
        "Verse": "vocal / groove",
        "Pre-Chorus": "lift / tension",
        "Chorus": "hook / full band",
        "Drop": "bass + lead + impact",
        "Bridge": "contrast / new melody",
        "Outro": "fade / resolve",
        "Breakdown": "strip back",
        "Build": "riser / filter",
    }.get(section, "core idea")


def effects_chain(role: str = "vocal") -> str:
    role = role.lower()
    chains = {
        "vocal": [
            "1. High-pass ~100 Hz",
            "2. De-esser (5-8 kHz)",
            "3. Compressor (3:1, medium attack)",
            "4. Auto-Tune / pitch correct (retune 15-40 ms, humanize on)",
            "5. EQ presence boost 3-5 kHz + air 10-12 kHz",
            "6. Saturation (subtle tape)",
            "7. Delay (1/8 dotted, low feedback, filtered)",
            "8. Reverb (plate or short hall, pre-delay 40 ms)",
        ],
        "drums": [
            "1. Kick: transient shaper + parallel compression + mono low-end",
            "2. Snare: body EQ + short plate + slap delay",
            "3. Hats: high-pass, stereo widen upper, light chorus optional",
            "4. Bus: glue compressor + clipper for loudness",
        ],
        "bass": [
            "1. High-pass 30 Hz",
            "2. Compression (slow attack for punch)",
            "3. Saturation / mild distortion for harmonics",
            "4. Sidechain to kick",
            "5. Keep mono below ~120 Hz",
        ],
        "synth": [
            "1. Filter (low-pass or high-pass movement)",
            "2. Chorus or unison for width",
            "3. Delay + reverb in parallel",
            "4. Sidechain for rhythm",
            "5. Stereo imager (protect lows)",
        ],
    }
    chain = chains.get(role, chains["vocal"])
    return f"Effects Processor recipe — {role.upper()}\n" + "\n".join(chain)


def auto_tuner_guide(style: str = "natural") -> str:
    styles = {
        "natural": "Retune speed 40-80 ms | Humanize 30-50% | Flex-tune medium | Scale = song key",
        "hard": "Retune speed 0-15 ms | Humanize 0-10% | Classic T-Pain / modern trap vocal",
        "melodic_rap": "Retune 10-25 ms | Formant shift mild | Scale minor pentatonic or key",
        "rnb": "Retune 25-50 ms | Throat modeling subtle | Add air + delay throws",
        "robot": "Retune 0 ms | Formant extreme | Bitcrush or vocoder layer optional",
    }
    tip = styles.get(style, styles["natural"])
    return (
        f"Auto-Tuner settings ({style}):\n"
        f"  {tip}\n"
        f"  Always set the correct key/scale first.\n"
        f"  Print the dry vocal parallel for emotion.\n"
        f"  Automate retune speed for phrases that need more human feel."
    )


def freestyle_prompt(genre: str = "hip-hop", bars: int = 8) -> str:
    themes = [
        "late night city lights", "rising from nothing", "loyalty and betrayal",
        "summer memories", "digital love", "hustle and peace", "lost connections",
        "victory lap", "inner demons", "new beginnings",
        "chamber strategy", "dusty basement cipher", "mask on / mask off",
        "survival math", "last transmission",
    ]
    flows = [
        "double-time", "laid-back pocket", "triplet", "syncopated",
        "call-and-response", "punchline stacked", "story-run", "switch-up every 4",
    ]
    genre_l = genre.lower()
    if any(w in genre_l for w in ("wu", "90s", "freestyle", "cipher")):
        themes += ["clan cipher", "street chess", "old booth energy"]
        flows += ["multis on the pass", "battle cadence"]
    if any(w in genre_l for w in ("suicide", "ghostemane", "horror", "lynch", "raided")):
        themes += ["blackout diary", "empty parking structure", "static on the wire"]
        flows += ["half-time crush", "whisper-to-bark"]
    if "eminem" in genre_l or "shady" in genre_l:
        themes += ["character in the mirror", "letter never sent"]
        flows += ["internal rhyme run", "persona switch"]
    theme = random.choice(themes)
    flow = random.choice(flows)
    return (
        f"FREESTYLE SEED — {genre.upper()} | {bars} bars\n"
        f"Theme  : {theme}\n"
        f"Flow   : {flow}\n"
        f"Key tip: Start with a strong opening image, land the rhyme on the 4, "
        f"leave space for ad-libs. Record 3 takes, keep the most alive one. Original bars only."
    )


def voice_mimic_notes(artist_style: str) -> str:
    """High-level stylistic notes only — no actual voice cloning or deepfake audio."""
    styles = {
        "drake": "Melodic half-sung delivery, introspective tone, sparse ad-libs, heavy reverb + delay throws, Auto-Tune medium-soft.",
        "the weeknd": "Falsetto runs, dark atmospheric production, long reverb tails, layered harmonies, cinematic pads.",
        "travis scott": "Psychedelic Auto-Tune, ad-lib heavy, distorted 808s, chopped vocal chops as instruments, atmospheric.",
        "sza": "Breathy intimate tone, flexible timing, jazz-tinged chords, soft compression, natural pitch variation.",
        "beyonce": "Powerful precise runs, gospel influence, dynamic control, tight harmonies, clean polished chain.",
        "billie eilish": "Whisper-close mic, minimal processing, ASMR intimacy, sub-bass, unusual textures.",
        # Wu-Tang (classic + modern)
        "wu-tang": "Raw chamber grit, off-kilter swing, martial-arts metaphor density, clan trade-offs, dusty boom-bap + eerie samples. Classic RZA: detuned loops, delayed snares. Modern: keep grit, tighter low end, light trap hats without losing swing.",
        "rza": "Abstract sample collage, detuned pianos, kung-fu dialogue chops, sparse drums, cinematic menace.",
        "ghostface": "Stream-of-consciousness urgency, vivid street-cinema imagery, emotional volatility, dense internal detail.",
        "gza": "Chess/strategy metaphors, measured authoritative tone, scientific rhyme precision.",
        "method man": "Raspy charisma, bounce cadence, call-and-response friendly, sticky ad-libs.",
        # 90s high-energy freestyle
        "90s freestyle": "High-BPM urgency, multisyllabic runs, punchline stacks, battle-rap aggression, live-cipher energy, minimal Auto-Tune, raw board/room mic presence.",
        "freestyle 90s": "High-BPM urgency, multisyllabic runs, punchline stacks, battle-rap aggression, live-cipher energy, minimal Auto-Tune, raw board/room mic presence.",
        # Underground / horrorcore / dark
        "suicideboys": "($uicideboy$) Memphis-influenced dark trap, triple-time hats, distorted 808s, bleak themes, chopped samples, heavy reverb ad-libs, lo-fi grit + modern sub.",
        "ghostemane": "Industrial trap-metal hybrid, harsh/screamed layers with rap, distorted synth/guitar, half-time or blast energy, blackened atmosphere, short aggressive forms.",
        "spazm": "Chaotic high-energy delivery, rapid pocket switches, frantic underground freestyle intensity.",
        "eminem": "Complex internals, character voices, rapid multis, story + shock punchlines, precise enunciation, whisper-to-bark dynamics; Dre polish or basement raw by era.",
        "brotha lynch": "Horrorcore narrative density, calm-menacing delivery, serial-story arcs, West Coast funk under dark fiction.",
        "x-raided": "Hardcore storytelling clarity, aggressive presence, classic 90s West Coast hardcore weight.",
        "mr kee": "Bay bounce, hyphy/hard callouts, regional cadence, lively ad-libs.",
        "mr doctor": "Horrorcore-adjacent dark narrative focus; grim atmosphere over melodic polish.",
        "12 step": "Confessional recovery/addiction framing, vulnerability vs hard exterior — concept/lyric use only, not instructional.",
        "default": "Study phrasing, vowel shapes, rhythmic placement, and emotional arc rather than exact timbre. "
                   "Use reference tracks for arrangement and effects only. Create original performances."
    }
    key = artist_style.lower().strip()
    for k in styles:
        if k in key:
            return (
                f"Artist / style notes ({k}):\n  {styles[k]}\n"
                f"  (Educational & inspiration only — no voice cloning. Write original bars.)"
            )
    return f"Artist voice style notes:\n  {styles['default']}"


# ---------------------------------------------------------------------------
# Concrete arrangement examples (genre playbooks)
# ---------------------------------------------------------------------------

ARRANGEMENT_EXAMPLES = {
    "trap": {
        "title": "Modern Trap Arrangement",
        "bpm": "140–160",
        "key_feel": "minor (often natural or harmonic)",
        "progression": "i – VI – III – VII  (or i – iv – VI – V)",
        "structure": [
            ("Intro 4–8 bars", "808 slide + sparse hats + atmospheric pad; no full kick pattern yet"),
            ("Verse 8–16", "Kick + 808 locked; hats rolling; melody minimal; space for vocal"),
            ("Chorus / Hook 8", "Full drums, open hats, layered melody or vocal chop, riser into hit"),
            ("Verse 2", "Add counter-melody or filtered chorus elements under vocal"),
            ("Bridge / Break 4–8", "Strip to 808 + vocal or switch swing; tension"),
            ("Final hook 8–16", "Maximum layers, ad-lib space, possible key lift or extra 808 fills"),
            ("Outro 4", "Filter down, remove hats, leave 808 tail"),
        ],
        "layers": {
            "drums": "Kick on 1 & syncopated; snare/clap 2+4; open/closed hat 1/8 or 1/16 rolls",
            "808": "Long decays, pitch slides into root, mono low end, sidechain light to kick",
            "melody": "Dark pluck or bell; pentatonic minor; leave gaps for vocal",
            "fx": "Riser before hook, impact on downbeat, vinyl/noise beds optional",
        },
        "tips": [
            "Hook first: write the catchiest 4–8 bars, then build verses around it",
            "808 and kick must not fight — tune 808 to key, duck slightly on kick",
            "Use silence as arrangement: drop hats for 1 bar before the hook hits",
        ],
    },
    "lofi": {
        "title": "Lo-fi Hip-Hop Arrangement",
        "bpm": "70–90",
        "key_feel": "jazzy minor / major 7 colors",
        "progression": "ii7 – V7 – Imaj7 – vi7  (or i7 – iv7 – bVII7 – III7)",
        "structure": [
            ("Intro 4–8", "Dusty chord loop + vinyl crackle; soft Rhodes or guitar"),
            ("A section 8–16", "Add soft kick/snare, muted bass, main sample or keys"),
            ("B section 8", "Chord variation or filtered flip; light percussion fill"),
            ("A return 8–16", "Full loop; optional soft vocal chop or lead"),
            ("Outro 4–8", "Elements exit one by one; leave chords + crackle"),
        ],
        "layers": {
            "drums": "Soft kick, snappy snare, swung hats; humanize timing heavily",
            "bass": "Round sub or upright-style; simple root movement",
            "harmony": "7th/9th chords, soft attack, tape saturation",
            "texture": "Vinyl noise, room tone, gentle sidechain to kick",
        },
        "tips": [
            "Imperfection is the aesthetic — slight timing and pitch drift help",
            "One strong loop can carry the whole track; arrangement = subtractive",
            "Keep master warm and not too loud; headroom is part of the vibe",
        ],
    },
    "pop": {
        "title": "Contemporary Pop Arrangement",
        "bpm": "100–128",
        "key_feel": "major or bright minor",
        "progression": "I – V – vi – IV  (or vi – IV – I – V)",
        "structure": [
            ("Intro 4–8", "Motif or filtered chorus hook; establish groove"),
            ("Verse 8", "Sparse drums + bass + one melodic element; vocal clear"),
            ("Pre-Chorus 4–8", "Add percussion, lift harmony, riser into chorus"),
            ("Chorus 8", "Full band, widest stereo, strongest melody/hook"),
            ("Verse 2", "Slightly fuller than V1; call-backs to chorus texture"),
            ("Pre + Chorus", "Same or bigger; optional double chorus"),
            ("Bridge 8", "New chords or stripped vocal; contrast then build"),
            ("Final chorus / outro", "Max energy then controlled exit or hard stop"),
        ],
        "layers": {
            "drums": "Punchy kick, crisp snare, 1/8 or 1/16 hats; fills into sections",
            "bass": "Synced to kick; simple and loud in the mix",
            "harmony": "Pads + plucks; suspend into chorus",
            "vocal": "Lead dry-ish in verse; stacked doubles + FX in chorus",
        },
        "tips": [
            "Chorus must feel like arrival — arrangement, not just volume",
            "Pre-chorus is the tension engine; don’t skip it",
            "One signature sound (riff, vocal texture) that returns = identity",
        ],
    },
    "edm": {
        "title": "EDM / Festival Drop Arrangement",
        "bpm": "126–150 (house/dubstep/hybrid vary)",
        "key_feel": "minor for dark drops; major for euphoric",
        "progression": "i – VI – III – VII  or single-chord tension beds",
        "structure": [
            ("Intro 8–16", "Atmosphere + filtered groove; DJ-friendly"),
            ("Build 8–16", "Snare rolls, rising noise, pitch risers, strip bass"),
            ("Drop 8–16", "Full bass + lead + drums; main hook",),
            ("Break 8", "Pads / vocal / ambient; reset energy"),
            ("Build 2 + Drop 2", "Variation on main drop; extra layers or switch lead"),
            ("Outro 8–16", "Filter down for mix-out"),
        ],
        "layers": {
            "drums": "Four-on-floor or half-time; heavy transient design",
            "bass": "Reese, growls, or supersaw subs depending on subgenre",
            "lead": "Memorable motif; automate filter and distortion",
            "fx": "Impacts, sweeps, reverse cymbals on every transition",
        },
        "tips": [
            "Drop must hit harder than the build promises — contrast is everything",
            "Leave the first kick of the drop clean for maximum impact",
            "Arrange for the dancefloor: energy curve > harmonic complexity",
        ],
    },
    "rnb": {
        "title": "Modern R&B Arrangement",
        "bpm": "60–95",
        "key_feel": "lush minor / major 7, 9, 11 chords",
        "progression": "Imaj7 – iii7 – vi7 – II7  or i7 – bVIImaj7 – bVImaj7 – V7",
        "structure": [
            ("Intro 4–8", "Chord bed + soft percussion or finger snaps"),
            ("Verse 8–16", "Intimate vocal, minimal drums, bass outlining harmony"),
            ("Pre 4", "Harmony thickens; background vocals enter"),
            ("Chorus 8", "Full keys + stacked vocals; groove opens"),
            ("Verse 2 / Bridge", "Call-and-response ad-libs; possible modulation feel"),
            ("Final chorus / outro", "Layered harmonies; gradual strip or vamp"),
        ],
        "layers": {
            "drums": "Soft kick, rim/snare, swung hats; ghost notes",
            "bass": "Melodic, interlocking with kick; sometimes synth sub + live tone",
            "keys": "Rhodes, soft piano, pads with slow attack",
            "vocal": "Lead + doubles + wide harmonies; dry verse, wet chorus",
        },
        "tips": [
            "Groove and vocal performance carry more than dense arrangement",
            "Leave low-mid space so the vocal sits forward",
            "Background vocals are arrangement tools — write them as parts",
        ],
    },
    "rock": {
        "title": "Rock / Indie Arrangement",
        "bpm": "110–140",
        "key_feel": "power-chord friendly major/minor",
        "progression": "I – bVII – IV – I  or i – bVI – bIII – bVII",
        "structure": [
            ("Intro 4–8", "Riff or drum entrance; establish identity"),
            ("Verse 8", "Cleaner guitars or half-band; vocal focus"),
            ("Pre / Climb 4", "Intensity up; snare build or extra guitar"),
            ("Chorus 8", "Full band, open chords, strongest melody"),
            ("Verse 2 + Chorus", "Add lead lines or second guitar"),
            ("Bridge / Solo 8", "New harmony or lead instrument"),
            ("Final chorus + outro", "Biggest energy then defined ending"),
        ],
        "layers": {
            "drums": "Live feel; fills into sections; room mics if possible",
            "bass": "Locks with kick; can take melodic fills in gaps",
            "guitars": "Rhythm left/right; lead in chorus/bridge",
            "vocal": "Doubles on chorus; gang vocals optional",
        },
        "tips": [
            "Riff identity > chord complexity for many rock tracks",
            "Dynamic contrast between verse and chorus is the arrangement",
            "Don’t over-layer; three strong parts often beat seven muddy ones",
        ],
    },
    "wu-tang": {
        "title": "Wu-Tang Style Arrangement (Classic → Modern)",
        "bpm": "85–105 classic | 120–140 modern hybrid",
        "key_feel": "minor, dusty, often modal or sample-driven",
        "progression": "Sample loop as harmony; or i – bVI – bVII – i",
        "structure": [
            ("Intro 4–8", "Dialogue/kung-fu chop or eerie motif; drums enter late"),
            ("Verse 8–16", "Boom-bap or swung drums; one MC; sample in pocket"),
            ("Hook 4–8", "Clan chant / memorable phrase; filtered sample lift"),
            ("Verse trade", "Next MC; slight drum or filter variation"),
            ("Bridge / skit", "Atmospheric break or dialogue"),
            ("Final verses + hook", "Energy up; ad-libs from multiple voices"),
            ("Outro", "Sample degrade or abrupt stop"),
        ],
        "layers": {
            "drums": "Classic: dusty kick/snare, swung hats. Modern: tighter low end, light 808 under kick",
            "sample": "Soul/jazz/film chops; detune; vinyl texture",
            "bass": "Round mono sub or sampled bass stab; leave room for kick",
            "vocal": "Dry-ish lead, group ad-libs, minimal Auto-Tune",
        },
        "tips": [
            "The sample is the song — arrange around its swing and dirt",
            "Trade verses keep energy; hooks stay short and chantable",
            "Modern Wu-inspired: don’t over-quantize; keep human swing",
        ],
    },
    "90s freestyle": {
        "title": "90s High-Energy Freestyle / Cipher Arrangement",
        "bpm": "90–110 (or faster battle tempo)",
        "key_feel": "minor or tense; often one-loop beds",
        "progression": "Single hard loop or i – bVII – bVI – V movement",
        "structure": [
            ("Drop-in 0–4", "Beat starts full; no long intro — cipher energy"),
            ("16 / 16 / 16", "Rotating freestylers or stacked verses; minimal hooks"),
            ("Break 2–4", "Drum fill or scratch; next writer jumps in"),
            ("Final run", "Best punchlines / fastest flows; crowd response space"),
            ("Out", "Hard cut or DJ scratch exit"),
        ],
        "layers": {
            "drums": "Hard kick/snare, busy hats optional; live feel over grid perfection",
            "loop": "One strong sample or synth stab; don’t over-arrange",
            "scratches": "Transform scratches on hooks or transitions",
            "vocal": "Raw, upfront, minimal FX — presence over polish",
        },
        "tips": [
            "Arrangement serves the freestyle — keep the bed stable so MCs can go",
            "Leave 1-bar pockets for breaths and punchline landings",
            "High energy = performance intensity, not just more instruments",
        ],
    },
    "suicideboys": {
        "title": "$uicideboy$ / Dark Underground Trap Arrangement",
        "bpm": "130–155 (or half-time feel ~70–80)",
        "key_feel": "minor, phrygian, or bleak modal colors",
        "progression": "i – VI – III – VII or single-chord drone under 808",
        "structure": [
            ("Intro 4–8", "Chopped sample or horror phrase; 808 enters"),
            ("Verse 8–16", "Triple hats, distorted 808, sparse melody; vocal dry/wet mix"),
            ("Hook 8", "Chantable bleak phrase; fuller drums; vocal layers"),
            ("Verse 2", "Switch flow or pitch; add industrial noise"),
            ("Break", "Strip to 808 + vocal or noise bed"),
            ("Final hook + outro", "Max distortion then abrupt or washed-out end"),
        ],
        "layers": {
            "drums": "Fast hats, hard clap/snare, punchy kick; optional industrial hits",
            "808": "Long, distorted, sliding; mono center; heavy",
            "sample": "Memphis/horror chops, pitched down, washed",
            "vocal": "Auto-Tune optional; doubles; long reverb tails on ad-libs",
        },
        "tips": [
            "Atmosphere > complexity — one strong dark texture carries far",
            "808 and vocal should feel oppressive but clear",
            "Silence and sudden drops hit harder than constant density",
        ],
    },
    "ghostemane": {
        "title": "Ghostemane / Industrial Trap-Metal Arrangement",
        "bpm": "140–180 or half-time crush",
        "key_feel": "minor / dissonant",
        "progression": "Power-chord or single-note riff beds; chromatic movement",
        "structure": [
            ("Intro", "Noise, feedback, or whispered line"),
            ("Verse", "Rap cadence over industrial beat or guitar"),
            ("Build", "Drums intensify; scream layer enters"),
            ("Drop / chorus", "Full distortion, harsh vocals, max impact"),
            ("Break", "Ambient or pure noise"),
            ("Final assault + cut", "Short — don’t overstay"),
        ],
        "layers": {
            "drums": "Acoustic + electronic hybrid; blasts or half-time",
            "guitars/synth": "Down-tuned or harsh digital distortion",
            "bass": "Distorted sub + mid grind",
            "vocal": "Rap + scream layers; aggressive compression",
        },
        "tips": [
            "Contrast whispered/rap sections with full harsh drops",
            "Keep songs short and structural punches sharp",
            "Mix: leave midrange for screams; sub for impact",
        ],
    },
    "eminem": {
        "title": "Eminem-Style Arrangement (Shady / Dre poles)",
        "bpm": "85–110 storytelling | faster for battle tracks",
        "key_feel": "minor for dark stories; major stabs for irony",
        "progression": "Loop-based or i – bVI – bIII – bVII; Dre-style sparse beds",
        "structure": [
            ("Intro", "Concept line, skit, or signature motif"),
            ("Verse 16–24", "Story or multi-syllable run; beat stays stable"),
            ("Hook 8", "Catchy, often melodic or chant; clearer mix"),
            ("Verse 2", "Escalate story or switch character/voice"),
            ("Bridge / breakdown", "Beat switch or stripped vocal moment"),
            ("Final verse + hook", "Peak intensity; possible double-time"),
            ("Outro", "Resolved line or abrupt shady cut"),
        ],
        "layers": {
            "drums": "Hard, clean kick/snare; occasional live feel",
            "melody": "Sparse — piano, strings, or guitar motif that leaves space",
            "bass": "Deep and simple; never crowds the vocal",
            "vocal": "Lead dry and present; character voices distinct; light FX only",
        },
        "tips": [
            "Vocal clarity is non-negotiable — arrange around the words",
            "Beat switches reward long storytelling arcs",
            "Hook should be simple enough to survive complex verses",
        ],
    },
    "horrorcore": {
        "title": "Horrorcore / West Coast Hard Arrangement (Lynch / X-Raided lane)",
        "bpm": "90–110",
        "key_feel": "minor, funk-dark, or cinematic dissonance",
        "progression": "i – iv – bVI – V or funk loops under dark narrative",
        "structure": [
            ("Intro", "Dialogue, news-chop, or eerie motif"),
            ("Verse", "Story-forward; beat steady so narrative lands"),
            ("Hook", "Memorable grim refrain; optional gang vocals"),
            ("Verse 2+", "Escalate narrative; maintain clarity"),
            ("Bridge", "Beat thin-out or key change for tension"),
            ("Final hook / outro", "Resolve or cut on a line"),
        ],
        "layers": {
            "drums": "West Coast bounce or hard boom-bap; clear pocket",
            "bass": "Funk-influenced or deep sustained notes",
            "sample/keys": "Horror stabs, minor keys, occasional soul under tension",
            "vocal": "Calm-menacing or aggressive-clear; minimal Auto-Tune",
        },
        "tips": [
            "Story is the arrangement — don’t bury the narrative under FX",
            "Contrast calm delivery with dark content for impact",
            "Keep low-mid clean so vocals stay intelligible",
        ],
    },
}


def arrangement_example(genre: str = "trap") -> str:
    g = genre.lower().strip()
    # fuzzy match
    for key in ARRANGEMENT_EXAMPLES:
        if key in g or g in key:
            g = key
            break
    else:
        g = "pop" if g not in ARRANGEMENT_EXAMPLES else g
    ex = ARRANGEMENT_EXAMPLES.get(g, ARRANGEMENT_EXAMPLES["pop"])
    lines = [
        f"═══ ARRANGEMENT EXAMPLE: {ex['title']} ═══",
        f"BPM range : {ex['bpm']}",
        f"Key feel  : {ex['key_feel']}",
        f"Progression idea: {ex['progression']}",
        "",
        "Structure",
        "─" * 56,
    ]
    for sec, detail in ex["structure"]:
        lines.append(f"  {sec}")
        lines.append(f"      {detail}")
    lines.append("")
    lines.append("Layer focus")
    lines.append("─" * 56)
    for role, detail in ex["layers"].items():
        lines.append(f"  {role:<10} {detail}")
    lines.append("")
    lines.append("Tips")
    lines.append("─" * 56)
    for t in ex["tips"]:
        lines.append(f"  • {t}")
    lines.append("")
    lines.append(
        "Ask for: trap | lofi | pop | edm | rnb | rock | wu-tang | 90s freestyle | "
        "suicideboys | ghostemane | eminem | horrorcore"
    )
    return "\n".join(lines)


def export_midi_sketch(sketch: SongSketch, path: str = "sketch.mid", bars: int = 8) -> Optional[str]:
    if not HAS_MIDI:
        return None
    midi = MIDIFile(1)
    track = 0
    midi.addTrackName(track, 0, sketch.title)
    midi.addTempo(track, 0, sketch.bpm)

    key_root = note_name_to_midi(sketch.key, 3)
    time = 0
    duration = 1  # quarter notes roughly

    for roman in sketch.progression * (bars // len(sketch.progression) + 1):
        if time >= bars * 4:
            break
        root, qual = roman_to_chord(roman, key_root, sketch.mode)
        chord = build_chord(root, qual)
        for note in chord:
            midi.addNote(track, 0, note, time, duration * 2, 80)
        # simple bass
        midi.addNote(track, 0, root - 12, time, duration * 2, 90)
        time += 2

    out = Path(path)
    with open(out, "wb") as f:
        midi.writeFile(f)
    return str(out.resolve())


def production_assistant(query: str) -> str:
    """Main entry — route a natural language request to the right tool."""
    q = query.lower()

    # Genre / composition
    if any(w in q for w in ("compose", "progression", "chord", "song idea", "sketch", "write a beat")):
        genre = next((g for g in GENRES if g in q), "pop")
        mood = "sad" if any(w in q for w in ("sad", "dark", "emotional")) else "uplifting"
        sketch = compose_sketch(genre=genre, mood=mood)
        return arrangement_map(sketch) + "\n\n(Type 'export midi' or ask for effects / auto-tune / freestyle next.)"

    if "arrang" in q or "structure" in q or "map" in q or "example" in q:
        # Prefer concrete genre example when genre is named
        genre = next((g for g in list(ARRANGEMENT_EXAMPLES.keys()) + GENRES if g in q), None)
        if genre or "example" in q:
            return arrangement_example(genre or "pop")
        sketch = compose_sketch()
        return arrangement_map(sketch)

    if "auto-tune" in q or "autotune" in q or "pitch correct" in q:
        style = "hard" if any(w in q for w in ("hard", "t-pain", "robot")) else "natural"
        if "trap" in q or "rap" in q:
            style = "melodic_rap"
        if "rnb" in q or "r&b" in q:
            style = "rnb"
        return auto_tuner_guide(style)

    if "effect" in q or "chain" in q or "mix" in q or "processor" in q:
        role = "vocal"
        if "drum" in q:
            role = "drums"
        elif "bass" in q:
            role = "bass"
        elif "synth" in q or "pad" in q:
            role = "synth"
        return effects_chain(role)

    if "freestyle" in q or "rap" in q or "bars" in q:
        genre = next((g for g in ("hip-hop", "trap", "drill", "r&b") if g in q), "hip-hop")
        return freestyle_prompt(genre)

    if any(w in q for w in ("voice", "mimic", "sound like", "style of")):
        # Extract possible artist
        artist = "default"
        for name in (
            "drake", "weeknd", "travis", "sza", "beyonce", "billie",
            "wu-tang", "rza", "ghostface", "gza", "method man",
            "90s freestyle", "freestyle 90s",
            "suicideboys", "ghostemane", "spazm", "eminem",
            "brotha lynch", "x-raided", "mr kee", "mr doctor", "12 step",
        ):
            if name in q:
                artist = name
                break
        return voice_mimic_notes(artist)

    if "midi" in q or "export" in q:
        sketch = compose_sketch()
        path = export_midi_sketch(sketch, "/home/workdir/artifacts/SVE_DualCore/sketch.mid")
        if path:
            return f"MIDI sketch exported → {path}\n\n" + arrangement_map(sketch)
        return "MIDI export unavailable (library missing). Here’s the arrangement instead:\n" + arrangement_map(sketch)

    if any(w in q for w in ("realtime", "render audio", "play progression", "audio engine", "wav")):
        try:
            from audio_engine import demo_realtime_progression, demo_freestyle, RealtimeEngine
            if "freestyle" in q:
                path = demo_freestyle()
                return f"Realtime freestyle rendered → {path}\n(Software engine @ 44.1 kHz, block streaming)"
            chords = ["Am", "F", "C", "G"]
            if "trap" in q:
                chords = ["Cm", "Ab", "Eb", "Bb"]
            elif "lofi" in q:
                chords = ["Am7", "Dm7", "G7", "Cmaj7"]
            path = demo_realtime_progression(chords=chords, bpm=96 if "lofi" in q else 128)
            return f"Realtime audio engine rendered → {path}\nChords: {chords}\n(Software block-based engine – no hardware I/O in this sandbox)"
        except Exception as e:
            return f"Audio engine error: {e}"

    # AI YouTube factory — Suno/Udio-ready packages
    if any(w in q for w in ("youtube", "suno", "udio", "ai music package", "generate prompt", "ai artist")):
        try:
            from ai_youtube_factory import full_package, list_styles, STYLE_DNA
            style = next((k for k in STYLE_DNA if k in q), "trap")
            theme = "night run"
            for word in ("theme", "about"):
                if word in q:
                    theme = q.split(word, 1)[-1].strip(" :.-")[:60] or theme
                    break
            return full_package(style, theme)
        except Exception as e:
            return f"(ai youtube factory error: {e})"

    # Default creative response
    sketch = compose_sketch()
    return (
        "Music Production Assistant ready.\n\n"
        + arrangement_map(sketch)
        + "\n\nTry: compose trap beat | auto-tune settings | vocal effects chain | "
        "freestyle 8 bars | sound like Drake (style notes) | export midi"
    )


# ---------------------------------------------------------------------------
# CLI / quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "compose a lofi sketch"
    print(production_assistant(query))
