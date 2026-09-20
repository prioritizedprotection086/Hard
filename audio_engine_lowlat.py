#!/usr/bin/env python3
"""
SVE DualCore Low-Latency Audio Engine
=====================================
Optimized for smallest practical block sizes.

Changes vs base engine:
  • Default block 128 samples (~2.9 ms) — can go to 64
  • Vectorized / reduced-Python-loop DSP where possible
  • Multi-layer (double / triple) voice stacking
  • Extensive benchmark & stress suite
  • Still software-only (no hardware I/O in sandbox)

Target: keep xRealtime >> 1.0 even under heavy polyphony + effects.
"""

from __future__ import annotations
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from pathlib import Path
import time
import json

SR = 44100
DEFAULT_BLOCK = 128          # ~2.9 ms

# ---------------------------------------------------------------------------
# Fast DSP
# ---------------------------------------------------------------------------

def midi_to_freq(midi: float) -> float:
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def note_to_midi(name: str) -> int:
    name = name.strip()
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
    symbol = symbol.strip()
    intervals = [0, 4, 7]
    root_name = symbol
    for q, iv in [
        ("maj7", [0, 4, 7, 11]), ("min7", [0, 3, 7, 10]), ("m7", [0, 3, 7, 10]),
        ("maj", [0, 4, 7]), ("min", [0, 3, 7]), ("m", [0, 3, 7]),
        ("7", [0, 4, 7, 10]), ("dim", [0, 3, 6]), ("aug", [0, 4, 8]),
        ("sus2", [0, 2, 7]), ("sus4", [0, 5, 7]),
    ]:
        if symbol.lower().endswith(q):
            root_name = symbol[:-len(q)]
            intervals = iv
            break
    root = note_to_midi(root_name + str(octave))
    return [root + i for i in intervals]


class FastOsc:
    """Phase-accurate oscillator with minimal state."""
    __slots__ = ("phase", "wave")
    def __init__(self, wave: str = "saw"):
        self.phase = 0.0
        self.wave = wave

    def render(self, freq: float, n: int, sr: int = SR) -> np.ndarray:
        # vectorized phase ramp
        ph = self.phase + np.arange(n, dtype=np.float64) * (freq / sr)
        self.phase = ph[-1] % 1.0 if n else self.phase
        ph = ph % 1.0
        if self.wave == "sine":
            return np.sin(2 * np.pi * ph)
        if self.wave == "square":
            return np.where(ph < 0.5, 1.0, -1.0)
        if self.wave == "triangle":
            return 1.0 - 4.0 * np.abs(ph - 0.5)
        # saw
        return 2.0 * ph - 1.0


class FastADSR:
    __slots__ = ("a", "d", "s", "r")
    def __init__(self, a=0.008, d=0.06, s=0.65, r=0.18):
        self.a, self.d, self.s, self.r = a, d, s, r

    def envelope(self, n: int, sr: int, gate: int) -> np.ndarray:
        env = np.zeros(n, dtype=np.float64)
        a_s = max(1, int(self.a * sr))
        d_s = max(1, int(self.d * sr))
        r_s = max(1, int(self.r * sr))
        # attack
        la = min(a_s, n)
        env[:la] = np.linspace(0, 1, la, endpoint=False)
        # decay
        start = a_s
        end = min(a_s + d_s, n)
        if end > start:
            env[start:end] = np.linspace(1, self.s, end - start, endpoint=False)
        # sustain
        sus_end = min(gate, n)
        if sus_end > end:
            env[end:sus_end] = self.s
        # release
        rs = sus_end
        re = min(rs + r_s, n)
        if re > rs:
            env[rs:re] = np.linspace(self.s, 0, re - rs, endpoint=False)
        return env


class FastLP:
    """One-pole lowpass – still recursive but tight loop."""
    __slots__ = ("z", "coeff")
    def __init__(self, cutoff: float = 5000.0, sr: int = SR):
        self.z = 0.0
        self.coeff = float(np.exp(-2 * np.pi * cutoff / sr))

    def process(self, x: np.ndarray) -> np.ndarray:
        y = np.empty_like(x)
        c, z = self.coeff, self.z
        # local vars for speed
        for i in range(len(x)):
            z = (1.0 - c) * x[i] + c * z
            y[i] = z
        self.z = z
        return y


class FastDelay:
    __slots__ = ("buf", "idx", "size")
    def __init__(self, max_ms: float = 600.0, sr: int = SR):
        self.size = int(max_ms * sr / 1000) + 1
        self.buf = np.zeros(self.size, dtype=np.float64)
        self.idx = 0

    def process(self, x: np.ndarray, delay_samp: int, fb: float = 0.3, mix: float = 0.25) -> np.ndarray:
        d = min(max(1, delay_samp), self.size - 1)
        y = np.empty_like(x)
        buf, idx, size = self.buf, self.idx, self.size
        for i in range(len(x)):
            delayed = buf[idx]
            y[i] = x[i] + delayed * mix
            buf[idx] = x[i] + delayed * fb
            idx = (idx + 1) % size
        self.idx = idx
        return y


class FastReverb:
    def __init__(self, sr: int = SR):
        self.ds = [FastDelay(120, sr) for _ in range(4)]
        self.taps = [int(t * sr / 1000) for t in (29, 43, 67, 89)]

    def process(self, x: np.ndarray, mix: float = 0.22) -> np.ndarray:
        wet = np.zeros_like(x)
        for d, t in zip(self.ds, self.taps):
            wet += d.process(x, t, fb=0.45, mix=1.0)
        wet *= 0.25
        return x * (1.0 - mix) + wet * mix


# ---------------------------------------------------------------------------
# Voice + Engine
# ---------------------------------------------------------------------------

@dataclass
class Voice:
    osc: FastOsc
    env: FastADSR
    freq: float
    samples_left: int
    velocity: float
    layer: int = 0          # 0 = main, 1 = double, 2 = triple
    kind: str = "synth"     # synth | 808 | kick


def render_808(n: int, freq: float, sr: int = SR) -> np.ndarray:
    """Classic 808-style sine with exponential pitch drop + long decay."""
    t = np.arange(n, dtype=np.float64) / sr
    # pitch envelope: start ~1.8x and drop to fundamental
    pitch_env = freq * (1.0 + 1.2 * np.exp(-t * 25.0))
    phase = np.cumsum(pitch_env / sr) * 2 * np.pi
    body = np.sin(phase)
    # amplitude: fast click + long boom
    amp = np.exp(-t * 3.5) * (1.0 - np.exp(-t * 80.0))
    # mild saturation
    return np.tanh(body * amp * 2.2)


def render_kick(n: int, freq: float = 55.0, sr: int = SR) -> np.ndarray:
    """Tighter kick: short pitch drop + click."""
    t = np.arange(n, dtype=np.float64) / sr
    pitch = freq * (1.0 + 3.0 * np.exp(-t * 40.0))
    phase = np.cumsum(pitch / sr) * 2 * np.pi
    body = np.sin(phase)
    amp = np.exp(-t * 8.0) * (1.0 - np.exp(-t * 120.0))
    click = np.exp(-t * 200.0) * np.sin(2 * np.pi * 3000 * t) * 0.35
    return np.tanh((body * amp + click) * 1.8)


class LowLatEngine:
    def __init__(self, bpm: float = 120.0, sr: int = SR, block: int = DEFAULT_BLOCK):
        self.sr = sr
        self.block = block
        self.bpm = bpm
        self.spb = int(sr * 60 / bpm)          # samples per beat
        self.voices: List[Voice] = []
        self.master = np.zeros(0, dtype=np.float32)
        self.t = 0
        self.lp = FastLP(5500, sr)
        self.delay = FastDelay(500, sr)
        self.reverb = FastReverb(sr)
        self.fx = {"filter": True, "delay": True, "reverb": True, "drive": False}
        self.layers = 1                        # 1 / 2 / 3
        self._808_cache: Dict[Tuple[int, int], np.ndarray] = {}

    def set_layers(self, n: int):
        self.layers = max(1, min(3, n))

    def note_on(self, midi: int, beats: float = 1.0, vel: float = 0.75, wave: str = "saw"):
        dur = int(beats * self.spb)
        for layer in range(self.layers):
            detune = 1.0 + (layer - (self.layers - 1) / 2) * 0.004
            level = vel * (0.7 if layer else 1.0)
            self.voices.append(Voice(
                osc=FastOsc(wave),
                env=FastADSR(),
                freq=midi_to_freq(midi) * detune,
                samples_left=dur,
                velocity=level,
                layer=layer,
                kind="synth",
            ))

    def hit_808(self, midi: int = 36, beats: float = 1.0, vel: float = 0.95):
        """Schedule a tuned 808 (midi 36 ≈ C1)."""
        dur = max(1, int(beats * self.spb))
        freq = midi_to_freq(midi)
        v = Voice(
            osc=FastOsc("sine"),
            env=FastADSR(0.001, 0.01, 0.3, 0.8),
            freq=freq,
            samples_left=dur,
            velocity=vel,
            kind="808",
        )
        v._wave = render_808(dur, freq, self.sr)
        v._pos = 0
        self.voices.append(v)

    def hit_kick(self, beats: float = 0.5, vel: float = 0.9):
        dur = max(1, int(beats * self.spb))
        v = Voice(
            osc=FastOsc("sine"),
            env=FastADSR(0.001, 0.01, 0.2, 0.3),
            freq=55.0,
            samples_left=dur,
            velocity=vel,
            kind="kick",
        )
        v._wave = render_kick(dur, 55.0, self.sr)
        v._pos = 0
        self.voices.append(v)

    def chord_on(self, symbol: str, beats: float = 2.0, octave: int = 3):
        notes = chord_notes(symbol, octave)
        for m in notes:
            self.note_on(m, beats, vel=0.5, wave="saw")
        # sine bass under chord
        self.note_on(notes[0] - 12, beats, vel=0.85, wave="sine")

    def process_block(self) -> np.ndarray:
        n = self.block
        buf = np.zeros(n, dtype=np.float64)
        alive = []
        for v in self.voices:
            if v.samples_left <= 0:
                continue
            take = min(n, v.samples_left)
            if v.kind in ("808", "kick"):
                chunk = v._wave[v._pos:v._pos + take]
                if len(chunk) < take:
                    chunk = np.pad(chunk, (0, take - len(chunk)))
                buf[:take] += chunk * v.velocity * (0.9 if v.kind == "808" else 0.85)
                v._pos += take
            else:
                raw = v.osc.render(v.freq, take, self.sr)
                env = v.env.envelope(take, self.sr, gate=v.samples_left)
                buf[:take] += raw * env * v.velocity * 0.28
            v.samples_left -= take
            if v.samples_left > 0:
                alive.append(v)
        self.voices = alive

        if self.fx["filter"]:
            buf = self.lp.process(buf)
        if self.fx["drive"]:
            buf = np.tanh(buf * 1.9)
        if self.fx["delay"]:
            dly = max(1, int(self.spb / 2))          # 1/8 note
            buf = self.delay.process(buf, dly, fb=0.28, mix=0.22)
        if self.fx["reverb"]:
            buf = self.reverb.process(buf, mix=0.18)

        buf = np.tanh(buf * 1.15)
        self.t += n
        return buf.astype(np.float32)

    def play_progression(self, chords: List[str], beats_per: float = 2.0, bars: int = 2,
                         with_808: bool = False, clear: bool = True):
        total_beats = len(chords) * beats_per * bars
        total = int(total_beats * self.spb)
        self.master = np.zeros(0, dtype=np.float32)
        self.t = 0
        if clear:
            self.voices.clear()
            self._808_cache.clear()
        next_ch = 0
        next_808 = 0
        idx = 0
        beat_i = 0
        rendered = 0
        while rendered < total:
            if self.t >= next_ch and idx < len(chords) * bars:
                self.chord_on(chords[idx % len(chords)], beats_per * 0.95)
                idx += 1
                next_ch += int(beats_per * self.spb)
            if with_808 and self.t >= next_808:
                self.hit_808(33 + (beat_i % 4), beats=0.95, vel=0.9)
                if beat_i % 2 == 0:
                    self.hit_kick(beats=0.3, vel=0.85)
                beat_i += 1
                next_808 += self.spb
            block = self.process_block()
            self.master = np.concatenate([self.master, block])
            rendered += self.block
        self.master = self.master[:total]

    def render(self, path: str) -> str:
        if len(self.master) == 0:
            return ""
        peak = np.max(np.abs(self.master)) + 1e-9
        audio = (self.master / peak * 0.88 * 32767).astype(np.int16)
        p = Path(path)
        wavfile.write(str(p), self.sr, audio)
        return str(p.resolve())


# ---------------------------------------------------------------------------
# Extensive test suite
# ---------------------------------------------------------------------------

def run_latency_matrix() -> List[Dict]:
    """Sweep until failure: block × layers × poly × 808 density."""
    results = []
    blocks = [32, 48, 64, 128]
    layers_list = [1, 2, 3]
    poly_list = [4, 8, 16]
    use_808_list = [False, True]

    print("=" * 78)
    print("FAILURE SWEEP  (OK ≥2.0x | TIGHT 1.1–2.0x | FAIL <1.1x)")
    print("=" * 78)
    print(f"{'Blk':>5} {'ms':>6} {'Lay':>4} {'Poly':>5} {'808':>4} {'xRT':>7}  Status")
    print("-" * 78)

    for block in blocks:
        lat_ms = block / SR * 1000
        for layers in layers_list:
            for poly in poly_list:
                for with_808 in use_808_list:
                    eng = LowLatEngine(bpm=140, block=block)
                    eng.set_layers(layers)
                    eng.fx["drive"] = with_808
                    for i in range(poly):
                        eng.note_on(48 + (i % 12), beats=12, vel=0.55)
                    if with_808:
                        # 808 every beat for stress
                        for b in range(8):
                            eng.hit_808(36 + (b % 3), beats=1.0, vel=0.9)
                            eng.hit_kick(beats=0.4, vel=0.85)
                    n_blocks = max(30, int(1.0 * SR / block))
                    t0 = time.perf_counter()
                    for _ in range(n_blocks):
                        eng.process_block()
                    dt = time.perf_counter() - t0
                    audio_s = n_blocks * block / SR
                    xrt = audio_s / dt if dt > 0 else 0
                    status = "OK" if xrt >= 2.0 else ("TIGHT" if xrt >= 1.1 else "FAIL")
                    rec = {
                        "block": block, "latency_ms": round(lat_ms, 2),
                        "layers": layers, "poly": poly, "with_808": with_808,
                        "x_realtime": round(xrt, 2), "status": status
                    }
                    results.append(rec)
                    flag = "✓" if status == "OK" else ("~" if status == "TIGHT" else "✗")
                    print(f"{block:5d} {lat_ms:6.2f} {layers:4d} {poly:5d} {str(with_808):>4} {xrt:7.2f}  {status} {flag}")
    return results


def run_quality_renders(out_dir: str = "/home/workdir/artifacts/SVE_DualCore") -> List[str]:
    paths = []
    configs = [
        (64, 2, ["Am", "F", "C", "G"], 96, False, "v2_64_double.wav"),
        (64, 2, ["Cm", "Ab", "Eb", "Bb"], 140, True, "v2_64_trap_808.wav"),
        (48, 2, ["Am", "F", "C", "G"], 100, True, "v2_48_double_808.wav"),
        (32, 1, ["Am7", "Dm7", "G7", "Cmaj7"], 85, False, "v2_32_lofi.wav"),
        (64, 3, ["Cm", "Ab", "Eb", "Bb"], 138, True, "v2_64_triple_808.wav"),
    ]
    print("\n" + "=" * 78)
    print("QUALITY + 808 RENDER PHASE")
    print("=" * 78)
    for block, layers, chords, bpm, use_808, name in configs:
        eng = LowLatEngine(bpm=bpm, block=block)
        eng.set_layers(layers)
        eng.fx["drive"] = use_808
        t0 = time.perf_counter()
        eng.play_progression(chords, beats_per=2.0, bars=2, with_808=use_808)
        path = eng.render(f"{out_dir}/{name}")
        dt = time.perf_counter() - t0
        dur = len(eng.master) / SR if len(eng.master) else 0
        paths.append(path)
        print(f"  {name}: {dur:.1f}s audio in {dt:.2f}s  (blk={block} lay={layers} 808={use_808})")
    return paths


def best_config(results: List[Dict]) -> Dict:
    # Prefer lowest latency with 808 on, layers=2, poly>=8, xRT>=2.5
    candidates = [
        r for r in results
        if r["with_808"] and r["layers"] == 2 and r["poly"] >= 8 and r["x_realtime"] >= 2.5
    ]
    if not candidates:
        candidates = [r for r in results if r["with_808"] and r["x_realtime"] >= 2.0]
    if not candidates:
        candidates = [r for r in results if r["x_realtime"] >= 2.0]
    if not candidates:
        return results[0]
    return min(candidates, key=lambda r: (r["latency_ms"], -r["x_realtime"]))


def failure_summary(results: List[Dict]) -> None:
    fails = [r for r in results if r["status"] == "FAIL"]
    tight = [r for r in results if r["status"] == "TIGHT"]
    print("\n" + "=" * 78)
    print("FAILURE ANALYSIS")
    print("=" * 78)
    print(f"Total configs tested: {len(results)}")
    print(f"FAIL  : {len(fails)}")
    print(f"TIGHT : {len(tight)}")
    if fails:
        print("\nFirst failures (lowest block / highest load):")
        for r in sorted(fails, key=lambda x: (x["block"], -x["poly"], -x["layers"]))[:8]:
            print(f"  block={r['block']} lay={r['layers']} poly={r['poly']} 808={r['with_808']} → {r['x_realtime']}x")


if __name__ == "__main__":
    results = run_latency_matrix()
    failure_summary(results)
    paths = run_quality_renders()
    best = best_config(results)
    print("\n" + "=" * 78)
    print("RECOMMENDED CONFIG (with 808)")
    print("=" * 78)
    print(json.dumps(best, indent=2))
    print("\nRendered files:")
    for p in paths:
        print(" ", p)
