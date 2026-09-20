#!/usr/bin/env python3
"""
SVE DualCore Realtime Audio Engine (software)
=============================================
Streaming synthesis + effects processor.

True hardware real-time I/O (mic/speakers) is not available in this
sandbox (no PortAudio / sounddevice). This engine provides:

  • Block-based "real-time" callback architecture
  • Oscillators, envelopes, filters
  • Effects: delay, simple reverb, distortion, pitch-shift (auto-tune-ish)
  • MIDI-triggered or freestyle note generation
  • Renders to WAV in streaming fashion
  • Integrates with music_assist sketches

Usage:
  from audio_engine import RealtimeEngine
  eng = RealtimeEngine(bpm=120)
  eng.play_progression(["Am", "F", "C", "G"], bars=4)
  eng.render("output.wav")
"""

from __future__ import annotations
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter, resample
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict
from pathlib import Path
import math
import time

SR = 44100          # sample rate
BLOCK = 512         # block size (~11.6 ms @ 44.1 kHz)


# ---------------------------------------------------------------------------
# DSP primitives
# ---------------------------------------------------------------------------

def midi_to_freq(midi: float) -> float:
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def note_to_midi(name: str) -> int:
    """'C4', 'Am', 'F#3' etc. Chords return root."""
    name = name.strip()
    # chord → root
    for q in ("maj7", "min7", "maj", "min", "m7", "m", "7", "dim", "aug", "sus2", "sus4"):
        if name.lower().endswith(q):
            name = name[:-len(q)]
            break
    note = name.rstrip("0123456789#-b")
    octave = 4
    for i, c in enumerate(name):
        if c.isdigit():
            octave = int(name[i:])
            note = name[:i]
            break
    base = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
            "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
            "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
    return 12 * (octave + 1) + base.get(note.upper().replace("♯", "#"), 0)


def chord_notes(symbol: str, octave: int = 3) -> List[int]:
    """Return MIDI notes for a simple chord symbol."""
    symbol = symbol.strip()
    root_name = symbol
    qual = "maj"
    for q, intervals in [
        ("maj7", [0, 4, 7, 11]), ("min7", [0, 3, 7, 10]), ("m7", [0, 3, 7, 10]),
        ("maj", [0, 4, 7]), ("min", [0, 3, 7]), ("m", [0, 3, 7]),
        ("7", [0, 4, 7, 10]), ("dim", [0, 3, 6]), ("aug", [0, 4, 8]),
        ("sus2", [0, 2, 7]), ("sus4", [0, 5, 7]),
    ]:
        if symbol.lower().endswith(q):
            root_name = symbol[:-len(q)]
            intervals_ = intervals
            break
    else:
        intervals_ = [0, 4, 7]
    root = note_to_midi(root_name + str(octave))
    return [root + i for i in intervals_]


class Oscillator:
    def __init__(self, waveform: str = "saw"):
        self.phase = 0.0
        self.waveform = waveform

    def render(self, freq: float, n: int, sr: int = SR) -> np.ndarray:
        t = (np.arange(n) + self.phase) / sr
        self.phase = (self.phase + n) % (sr / max(freq, 1e-6) * sr)  # keep bounded
        if self.waveform == "sine":
            return np.sin(2 * np.pi * freq * t)
        if self.waveform == "square":
            return np.sign(np.sin(2 * np.pi * freq * t))
        if self.waveform == "triangle":
            return 2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1
        # saw
        return 2 * (t * freq - np.floor(0.5 + t * freq))


class ADSR:
    def __init__(self, a=0.01, d=0.1, s=0.7, r=0.2):
        self.a, self.d, self.s, self.r = a, d, s, r

    def envelope(self, n: int, sr: int = SR, gate_samples: Optional[int] = None) -> np.ndarray:
        if gate_samples is None:
            gate_samples = n
        env = np.zeros(n)
        a_s = int(self.a * sr)
        d_s = int(self.d * sr)
        r_s = int(self.r * sr)
        # attack
        if a_s > 0:
            env[:min(a_s, n)] = np.linspace(0, 1, min(a_s, n))
        # decay
        start = a_s
        end = min(a_s + d_s, n)
        if end > start:
            env[start:end] = np.linspace(1, self.s, end - start)
        # sustain
        sustain_end = min(gate_samples, n)
        if sustain_end > end:
            env[end:sustain_end] = self.s
        # release
        rel_start = sustain_end
        rel_end = min(rel_start + r_s, n)
        if rel_end > rel_start:
            env[rel_start:rel_end] = np.linspace(self.s, 0, rel_end - rel_start)
        return env


class OnePoleLP:
    def __init__(self, cutoff: float = 2000.0, sr: int = SR):
        self.z = 0.0
        self.set_cutoff(cutoff, sr)

    def set_cutoff(self, cutoff: float, sr: int = SR):
        self.coeff = np.exp(-2 * np.pi * cutoff / sr)

    def process(self, x: np.ndarray) -> np.ndarray:
        y = np.empty_like(x)
        c = self.coeff
        z = self.z
        for i, s in enumerate(x):
            z = (1 - c) * s + c * z
            y[i] = z
        self.z = z
        return y


class Delay:
    def __init__(self, max_ms: float = 1000.0, sr: int = SR):
        self.buf = np.zeros(int(max_ms * sr / 1000) + 1)
        self.idx = 0
        self.sr = sr

    def process(self, x: np.ndarray, delay_ms: float = 350, feedback: float = 0.35, mix: float = 0.3) -> np.ndarray:
        d = int(delay_ms * self.sr / 1000)
        d = min(d, len(self.buf) - 1)
        y = np.empty_like(x)
        for i, s in enumerate(x):
            delayed = self.buf[self.idx]
            out = s + delayed * mix
            self.buf[self.idx] = s + delayed * feedback
            self.idx = (self.idx + 1) % len(self.buf)
            y[i] = out
        return y


class SimpleReverb:
    """Very lightweight Schroeder-style approximation."""
    def __init__(self, sr: int = SR):
        self.delays = [Delay(100, sr) for _ in range(4)]
        self.times = [31, 47, 71, 97]  # ms

    def process(self, x: np.ndarray, mix: float = 0.25) -> np.ndarray:
        wet = np.zeros_like(x)
        for d, t in zip(self.delays, self.times):
            wet += d.process(x, delay_ms=t, feedback=0.5, mix=1.0)
        wet *= 0.25
        return x * (1 - mix) + wet * mix


class SoftClip:
    def process(self, x: np.ndarray, drive: float = 1.5) -> np.ndarray:
        return np.tanh(x * drive)


class PitchShift:
    """Crude real-time-ish pitch shifter via resampling (for auto-tune demo)."""
    def __init__(self):
        self.buf = np.zeros(0)

    def process(self, x: np.ndarray, semitones: float = 0.0) -> np.ndarray:
        if abs(semitones) < 0.01:
            return x
        ratio = 2.0 ** (semitones / 12.0)
        n_out = int(len(x) / ratio)
        if n_out < 1:
            return x
        y = resample(x, n_out)
        # pad or trim to original length
        if len(y) < len(x):
            y = np.pad(y, (0, len(x) - len(y)))
        else:
            y = y[:len(x)]
        return y


# ---------------------------------------------------------------------------
# Realtime Engine
# ---------------------------------------------------------------------------

@dataclass
class Voice:
    osc: Oscillator
    env: ADSR
    freq: float = 0.0
    active: bool = False
    samples_left: int = 0
    velocity: float = 0.8


class RealtimeEngine:
    def __init__(self, bpm: float = 120.0, sr: int = SR, block: int = BLOCK):
        self.sr = sr
        self.block = block
        self.bpm = bpm
        self.samples_per_beat = int(sr * 60 / bpm)
        self.voices: List[Voice] = []
        self.master = np.zeros(0, dtype=np.float32)
        self.time_samples = 0
        self.lp = OnePoleLP(4000, sr)
        self.delay = Delay(800, sr)
        self.reverb = SimpleReverb(sr)
        self.clip = SoftClip()
        self.pitch = PitchShift()
        self.effects_enabled = {
            "filter": True,
            "delay": True,
            "reverb": True,
            "drive": False,
            "autotune": False,
        }
        self.autotune_semitones = 0.0  # global shift for demo

    def note_on(self, midi: int, duration_beats: float = 1.0, velocity: float = 0.8, wave: str = "saw"):
        v = Voice(
            osc=Oscillator(wave),
            env=ADSR(0.01, 0.08, 0.6, 0.25),
            freq=midi_to_freq(midi),
            active=True,
            samples_left=int(duration_beats * self.samples_per_beat),
            velocity=velocity,
        )
        self.voices.append(v)

    def chord_on(self, symbol: str, duration_beats: float = 2.0, octave: int = 3):
        for m in chord_notes(symbol, octave):
            self.note_on(m, duration_beats, velocity=0.55, wave="saw")
        # bass
        root = chord_notes(symbol, octave - 1)[0]
        self.note_on(root, duration_beats, velocity=0.85, wave="sine")

    def process_block(self) -> np.ndarray:
        buf = np.zeros(self.block, dtype=np.float64)
        still_active = []
        for v in self.voices:
            if not v.active or v.samples_left <= 0:
                continue
            n = min(self.block, v.samples_left)
            raw = v.osc.render(v.freq, n, self.sr)
            env = v.env.envelope(n, self.sr, gate_samples=v.samples_left)
            buf[:n] += raw * env * v.velocity * 0.3
            v.samples_left -= n
            if v.samples_left > 0:
                still_active.append(v)
        self.voices = still_active

        # effects chain
        if self.effects_enabled["filter"]:
            buf = self.lp.process(buf)
        if self.effects_enabled["drive"]:
            buf = self.clip.process(buf, drive=1.8)
        if self.effects_enabled["delay"]:
            buf = self.delay.process(buf, delay_ms=60_000 / self.bpm / 2, feedback=0.3, mix=0.25)  # 1/8 note
        if self.effects_enabled["reverb"]:
            buf = self.reverb.process(buf, mix=0.2)
        if self.effects_enabled["autotune"] and abs(self.autotune_semitones) > 0.01:
            buf = self.pitch.process(buf, self.autotune_semitones)

        # soft limit
        buf = np.tanh(buf * 1.2)
        self.time_samples += self.block
        return buf.astype(np.float32)

    def play_progression(self, chords: List[str], beats_per_chord: float = 4.0, bars: int = 1):
        """Schedule a chord progression (blocks until rendered into master)."""
        total_beats = len(chords) * beats_per_chord * bars
        total_samples = int(total_beats * self.samples_per_beat)
        self.master = np.zeros(0, dtype=np.float32)

        chord_idx = 0
        next_chord_sample = 0
        rendered = 0

        while rendered < total_samples:
            if self.time_samples >= next_chord_sample and chord_idx < len(chords) * bars:
                ch = chords[chord_idx % len(chords)]
                self.chord_on(ch, duration_beats=beats_per_chord * 0.95)
                chord_idx += 1
                next_chord_sample += int(beats_per_chord * self.samples_per_beat)

            block = self.process_block()
            self.master = np.concatenate([self.master, block])
            rendered += self.block

        # trim
        self.master = self.master[:total_samples]

    def freestyle_notes(self, scale_midi: List[int], beats: float = 8.0, density: float = 0.6):
        """Generate a simple melodic freestyle over a scale."""
        total_samples = int(beats * self.samples_per_beat)
        self.master = np.zeros(0, dtype=np.float32)
        rendered = 0
        next_note = 0
        while rendered < total_samples:
            if self.time_samples >= next_note and random_chance(density):
                note = int(np.random.choice(scale_midi))
                dur = np.random.choice([0.25, 0.5, 0.75, 1.0])
                self.note_on(note, dur, velocity=0.6 + 0.3 * np.random.rand(), wave="sine")
                next_note = self.time_samples + int(dur * self.samples_per_beat * 0.8)
            block = self.process_block()
            self.master = np.concatenate([self.master, block])
            rendered += self.block
        self.master = self.master[:total_samples]

    def render(self, path: str = "realtime_out.wav") -> str:
        if len(self.master) == 0:
            return ""
        # normalize
        peak = np.max(np.abs(self.master)) + 1e-9
        audio = (self.master / peak * 0.89 * 32767).astype(np.int16)
        out = Path(path)
        wavfile.write(str(out), self.sr, audio)
        return str(out.resolve())

    def set_effect(self, name: str, on: bool = True):
        if name in self.effects_enabled:
            self.effects_enabled[name] = on

    def set_autotune(self, semitones: float = 0.0, enable: bool = True):
        self.autotune_semitones = semitones
        self.effects_enabled["autotune"] = enable


def random_chance(p: float) -> bool:
    return np.random.rand() < p


# ---------------------------------------------------------------------------
# Convenience demo / integration
# ---------------------------------------------------------------------------

def demo_realtime_progression(
    chords: Optional[List[str]] = None,
    bpm: float = 96,
    out_path: str = "/home/workdir/artifacts/SVE_DualCore/realtime_demo.wav",
) -> str:
    chords = chords or ["Am", "F", "C", "G"]
    eng = RealtimeEngine(bpm=bpm)
    eng.set_effect("delay", True)
    eng.set_effect("reverb", True)
    eng.set_effect("filter", True)
    print(f"Rendering {chords} @ {bpm} BPM …")
    t0 = time.time()
    eng.play_progression(chords, beats_per_chord=2.0, bars=2)
    path = eng.render(out_path)
    dt = time.time() - t0
    print(f"Rendered {len(eng.master)/SR:.1f}s of audio in {dt:.2f}s → {path}")
    return path


def demo_freestyle(
    key: str = "A",
    bpm: float = 140,
    out_path: str = "/home/workdir/artifacts/SVE_DualCore/freestyle_demo.wav",
) -> str:
    # A minor pentatonic
    root = note_to_midi(key + "4")
    scale = [root + i for i in (0, 3, 5, 7, 10, 12, 15, 17)]
    eng = RealtimeEngine(bpm=bpm)
    eng.set_effect("delay", True)
    eng.set_effect("reverb", True)
    print(f"Freestyle in {key} minor pentatonic @ {bpm} BPM …")
    eng.freestyle_notes(scale, beats=8.0, density=0.7)
    path = eng.render(out_path)
    print(f"→ {path}")
    return path


if __name__ == "__main__":
    import sys
    if "freestyle" in " ".join(sys.argv).lower():
        demo_freestyle()
    else:
        demo_realtime_progression()
