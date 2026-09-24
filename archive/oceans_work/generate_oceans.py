#!/usr/bin/env python3
"""PREACH FLOW — stems 'Oceans' (instrumental worship original, progressões públicas).
Harmonia estilo Oceans (Where Feet May Fail): Bm - A/C# - D - A - G | chorus G - D - A.
10 WAV mono sincronizados + mix de referência. build → clímax."""
import math
import os
import wave

import numpy as np
from scipy.signal import lfilter

SR = 44100
BPM = 72.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
N_BARS = 56
DUR = N_BARS * BAR
N = int(DUR * SR)
rng = np.random.default_rng(11)

OUT = os.path.dirname(os.path.abspath(__file__))
WAVS = os.path.join(OUT, "wavs")
os.makedirs(WAVS, exist_ok=True)

STEMS = [
    "Backing_Vocals", "Drums", "Bass", "Keyboard", "Percussion",
    "Strings", "Synth", "FX", "Brass", "Woodwinds",
]

# ---- MIDI ----
# C4=60. Intervals; chords as (triad_root_midi, quality, bass_midi)
Bm = (59, "min", 47)       # B D F# / bass B2
A_Cs = (57, "maj", 49)     # A C# E / bass C#3  (A/C#)
D_ = (62, "maj", 50)       # D F# A / bass D3
A_ = (57, "maj", 45)       # A C# E / bass A2
G_ = (55, "maj", 43)       # G B D / bass G2

SEC = {
    "intro": (0, 8),
    "verse": (8, 24),
    "build": (24, 32),
    "chorus": (32, 48),
    "outro": (48, 56),
}

# Bar-by-bar plan (56 bars): correct Oceans DNA
# intro:  Bm A/C# D A | Bm A/C# D G
# verse:  Bm A/C# D A | G D A A  x2
# build:  Bm G D A    | Bm G D A (riser)
# chorus: G D A Bm    | G D A A  x2
# outro:  Bm A/C# D A | G D A D (resolve)
def _pat(seq, n):
    return [seq[i % len(seq)] for i in range(n)]

PLAN = (
    _pat([Bm, A_Cs, D_, A_, Bm, A_Cs, D_, G_], 8)          # 0-8 intro
    + _pat([Bm, A_Cs, D_, A_, G_, D_, A_, A_], 16)          # 8-24 verse (2x8)
    + _pat([Bm, G_, D_, A_, Bm, G_, D_, A_], 8)             # 24-32 build
    + _pat([G_, D_, A_, Bm, G_, D_, A_, A_], 16)            # 32-48 chorus (2x8)
    + _pat([Bm, A_Cs, D_, A_, G_, D_, A_, D_], 8)           # 48-56 outro
)
assert len(PLAN) == N_BARS

def in_section(bar, name):
    a, b = SEC[name]
    return a <= bar < b

def section_of(bar):
    for name, (a, b) in SEC.items():
        if a <= bar < b:
            return name
    return "outro"

def t_of(bar, beat=0.0):
    return bar * BAR + beat * BEAT

def idx(sec):
    return int(max(0, min(N - 1, round(sec * SR))))

def env_adsr(n, a, d, s, r, sr=SR):
    a_n, d_n, r_n = int(a * sr), int(d * sr), int(r * sr)
    s_n = max(0, n - a_n - d_n - r_n)
    parts = [
        np.linspace(0, 1, a_n, endpoint=False) if a_n else np.array([]),
        np.linspace(1, s, d_n, endpoint=False) if d_n else np.array([]),
        np.full(s_n, s),
        np.linspace(s, 0, r_n) if r_n else np.array([]),
    ]
    e = np.concatenate([p for p in parts if len(p)])
    if len(e) < n:
        e = np.pad(e, (0, n - len(e)))
    return e[:n]

def add(buf, sig, start_sec):
    i0 = idx(start_sec)
    i1 = min(N, i0 + len(sig))
    if i0 >= N or i1 <= i0:
        return
    buf[i0:i1] += sig[: i1 - i0]

def midi_hz(m):
    return 440.0 * (2.0 ** ((m - 69) / 12.0))

def saw(freq, n, detune=0.0):
    t = np.arange(n) / SR
    f = freq * (1 + detune)
    ph = (t * f) % 1.0
    return 2.0 * ph - 1.0

def soft_clip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive) if drive > 0 else x

def biquad_lp(x, fc, q=0.707, sr=SR):
    fc = float(min(max(fc, 20.0), sr * 0.49))
    w0 = 2 * math.pi * fc / sr
    alpha = math.sin(w0) / (2 * q)
    cosw = math.cos(w0)
    b = np.array([(1 - cosw) / 2, 1 - cosw, (1 - cosw) / 2])
    a = np.array([1 + alpha, -2 * cosw, 1 - alpha])
    return lfilter(b / a[0], a / a[0], x)

def biquad_hp(x, fc, q=0.707, sr=SR):
    fc = float(min(max(fc, 20.0), sr * 0.49))
    w0 = 2 * math.pi * fc / sr
    alpha = math.sin(w0) / (2 * q)
    cosw = math.cos(w0)
    b = np.array([(1 + cosw) / 2, -(1 + cosw), (1 + cosw) / 2])
    a = np.array([1 + alpha, -2 * cosw, 1 - alpha])
    return lfilter(b / a[0], a / a[0], x)

def chord_ivs(quality):
    if quality == "maj":
        return [0, 4, 7, 12]
    if quality == "min":
        return [0, 3, 7, 12]
    return [0, 5, 7, 12]

def chord_midis(root, quality, octave=0):
    return [root + i + 12 * octave for i in chord_ivs(quality)]

def cell(bar):
    return PLAN[bar]

# ========== VOICES ==========

def voice_keyboard(buf, bar):
    root, quality, bass = cell(bar)
    notes = chord_midis(root, quality, 0)
    # Oceans-like piano arpeggio: root - fifth - third - fifth (8th feel in chorus)
    arp = [notes[0], notes[2], notes[1], notes[2], notes[0] + 12, notes[2], notes[1], notes[3] if len(notes) > 3 else notes[2]]
    sec = section_of(bar)
    dense = sec in ("build", "chorus")
    steps = 8 if dense else 4
    # Intro: only sustained soft chord + sparse arpeggio (piano-led)
    if sec == "intro":
        for s in (0, 2):
            m = arp[s % len(arp)]
            f = midi_hz(m)
            dur = BEAT * 2
            n = int(dur * SR)
            tt = np.arange(n) / SR
            env = np.exp(-tt * 1.6) * env_adsr(n, 0.015, 0.08, 0.65, 0.4)
            sig = sum(
                amp * np.sin(2 * np.pi * f * k * tt)
                for k, amp in enumerate([1.0, 0.4, 0.18, 0.08, 0.04], start=1)
                if f * k < 9000
            )
            add(buf, sig * env * 0.1, t_of(bar, s * 1.0))
        n = int(BAR * SR)
        tt = np.arange(n) / SR
        env = env_adsr(n, 0.5, 0.4, 0.5, 1.0)
        chord = np.zeros(n)
        for m in notes[:3]:
            f = midi_hz(m)
            chord += np.sin(2 * np.pi * f * tt) * 0.045
        add(buf, chord * env, t_of(bar))
        return
    for s in range(steps):
        m = arp[s % len(arp)]
        if not dense and s % 2 == 1:
            continue
        f = midi_hz(m)
        dur = BEAT * (1.0 if dense else 1.5)
        n = int(dur * SR)
        tt = np.arange(n) / SR
        env = np.exp(-tt * 2.2) * env_adsr(n, 0.01, 0.05, 0.7, 0.3)
        sig = np.zeros(n)
        for k, amp in enumerate([1.0, 0.45, 0.22, 0.12, 0.06], start=1):
            if f * k > 8000:
                break
            sig += amp * np.sin(2 * np.pi * f * k * tt + 0.1 * k)
        lvl = 0.1
        if sec == "chorus":
            lvl = 0.12
        if sec == "outro":
            lvl = 0.085
        add(buf, sig * env * lvl, t_of(bar, s * (4.0 / steps)))
    n = int(BAR * SR)
    tt = np.arange(n) / SR
    env = env_adsr(n, 0.35, 0.3, 0.55, 0.8)
    chord = np.zeros(n)
    for m in notes[:3]:
        f = midi_hz(m + 12)
        chord += np.sin(2 * np.pi * f * tt) * 0.035
        chord += 0.3 * np.sin(2 * np.pi * f * 2 * tt) * 0.018
    add(buf, chord * env, t_of(bar))

def voice_bass(buf, bar):
    root, quality, bass = cell(bar)
    sec = section_of(bar)
    if sec == "intro" and bar < 4:
        return
    if sec == "intro" and bar % 2 == 0:
        # soft long root only late intro
        f = midi_hz(bass)
        n = int(BAR * SR)
        tt = np.arange(n) / SR
        env = env_adsr(n, 0.4, 0.4, 0.5, 0.9)
        add(buf, np.sin(2 * np.pi * f * tt) * env * 0.12, t_of(bar))
        return
    if sec in ("intro",) and bar % 2 == 1:
        return
    pattern = [0, 0, 7, 0] if sec in ("chorus", "build") else [0, None, 0, None]
    if sec == "outro":
        pattern = [0, None, None, None]
    for bi, iv in enumerate(pattern):
        if iv is None:
            continue
        m = bass + iv
        if m < 28:
            m += 12
        f = midi_hz(m)
        dur = BEAT * (1.0 if bi in (0, 2) else 0.75)
        n = int(dur * SR)
        tt = np.arange(n) / SR
        env = env_adsr(n, 0.02, 0.08, 0.6, 0.15) * np.exp(-tt * 0.8)
        sig = np.sin(2 * np.pi * f * tt) + 0.25 * saw(f, n) + 0.15 * np.sin(2 * np.pi * f * 0.5 * tt)
        lvl = 0.22
        if sec == "verse":
            lvl = 0.18
        if sec == "chorus":
            lvl = 0.26
        add(buf, soft_clip(sig * env * lvl, 1.4), t_of(bar, bi))

def voice_strings(buf, bar):
    root, quality, bass = cell(bar)
    sec = section_of(bar)
    if bar < 12:
        return
    notes = chord_midis(root, quality, 1)
    n = int(BAR * SR)
    tt = np.arange(n) / SR
    level = 0.03
    if sec == "build":
        level = 0.055
    if sec == "chorus":
        level = 0.08
    if sec == "outro":
        level = 0.04
    env = env_adsr(n, 0.8, 0.5, 0.7, 1.0)
    sig = np.zeros(n)
    for m in notes:
        f = midi_hz(m)
        for det in (-0.006, 0.0, 0.007):
            vib = 1 + 0.003 * np.sin(2 * np.pi * 5.2 * tt)
            s = 2 * ((tt * f * vib + det) % 1.0) - 1
            sig += s
    sig = biquad_lp(sig, 5000 if sec == "chorus" else 3200, 0.7)
    add(buf, sig * env * level / 4, t_of(bar))

def voice_synth(buf, bar):
    root, quality, bass = cell(bar)
    sec = section_of(bar)
    if sec == "intro" or bar < 16:
        return
    if sec == "verse" and bar < 20:
        return
    notes = chord_midis(root, quality, 1)
    n = int(BAR * SR)
    tt = np.arange(n) / SR
    level = 0.04 if sec == "build" else (0.065 if sec == "chorus" else 0.035)
    env = env_adsr(n, 0.6, 0.4, 0.75, 0.9)
    fc = 1100 if sec == "chorus" else (700 if sec == "build" else 550)
    sig = np.zeros(n)
    for m in notes:
        f = midi_hz(m)
        for det in (-0.01, 0.012):
            sig += saw(f, n, det)
    sig = biquad_lp(sig, fc, 1.1)
    pulse = 0.7 + 0.3 * np.sin(2 * np.pi * (1 / BEAT) * tt)
    add(buf, soft_clip(sig * env * pulse * level / 4, 1.2), t_of(bar))

def voice_brass(buf, bar):
    root, quality, bass = cell(bar)
    sec = section_of(bar)
    # brass only in chorus peak (second half) and early outro hits
    if sec == "chorus" and bar < 40:
        return
    if sec == "outro" and bar >= 52:
        return
    if sec not in ("chorus", "outro"):
        return
    if sec == "chorus" and (bar - 40) % 2 != 0:
        return
    if sec == "outro" and bar not in (48, 50):
        return
    notes = chord_midis(root, quality, 0)
    n = int(BEAT * 3 * SR)
    tt = np.arange(n) / SR
    env = env_adsr(n, 0.08, 0.4, 0.55, 0.8)
    sig = np.zeros(n)
    for m in notes[:3]:
        f = midi_hz(m + 12)
        sig += saw(f, n, 0.004) + saw(f, n, -0.005)
    sig = biquad_lp(sig, 2800, 0.9)
    add(buf, sig * env * 0.05 / 3, t_of(bar, 0))
    add(buf, sig * env * 0.032 / 3, t_of(bar, 2))

def voice_woodwinds(buf, bar):
    root, quality, bass = cell(bar)
    sec = section_of(bar)
    if sec not in ("build", "chorus"):
        return
    # flute counter-line on chord tones (not the famous vocal melody)
    notes = chord_midis(root, quality, 1)
    scale = [0, 2, 4, 5, 7, 9, 11]
    melody_deg = [0, 2, 4, 2, 7, 4, 2, 0]
    steps = 4
    for s in range(steps):
        deg = melody_deg[(bar * steps + s) % len(melody_deg)]
        if s % 2 == 1 and sec == "build":
            continue
        m = root + 12 + scale[deg % 7] + 12 * (deg // 7)
        f = midi_hz(m)
        dur = BEAT * 0.9
        n = int(dur * SR)
        tt = np.arange(n) / SR
        vib = 1 + 0.008 * np.sin(2 * np.pi * 5.5 * tt)
        sig = np.sin(2 * np.pi * f * vib * tt)
        sig += 0.35 * np.sin(2 * np.pi * 3 * f * vib * tt)
        sig += 0.12 * np.sin(2 * np.pi * 5 * f * vib * tt)
        breath = rng.standard_normal(n) * 0.008
        breath = biquad_hp(breath, f * 0.8)
        env = env_adsr(n, 0.06, 0.1, 0.75, 0.2)
        level = 0.04 if sec == "chorus" else 0.025
        add(buf, (sig * env + breath * env) * level, t_of(bar, s))

def voice_drums(buf, bar):
    sec = section_of(bar)
    if sec == "intro":
        # soft pulse entering mid-intro
        if bar < 4:
            return
        n = int(0.3 * SR)
        tt = np.arange(n) / SR
        f = 90 * np.exp(-tt * 20) + 42
        phase = 2 * np.pi * np.cumsum(f) / SR
        add(buf, np.sin(phase) * np.exp(-tt * 10) * 0.35, t_of(bar, 0))
        return
    soft = sec == "verse"
    build = sec == "build"
    hard = sec == "chorus"
    if sec == "outro" and bar >= 52:
        return
    kicks = [0, 2] if not hard else [0, 1.5, 2, 3.5]
    if soft:
        kicks = [0, 2] if bar % 2 == 0 else [0]
    if build:
        kicks = [0, 2] if bar < 28 else [0, 1.5, 2, 3]
    for kb in kicks:
        n = int(0.35 * SR)
        tt = np.arange(n) / SR
        f = 120 * np.exp(-tt * 18) + 45
        phase = 2 * np.pi * np.cumsum(f) / SR
        env = np.exp(-tt * 9)
        sig = np.sin(phase) * env
        click = rng.standard_normal(n) * np.exp(-tt * 80) * 0.15
        add(buf, (sig + click) * (0.5 if soft else 0.78), t_of(bar, kb))
    if not soft or build:
        snares = [1, 3] if hard else ([1, 3] if build else ([1] if bar % 2 == 1 else []))
        for sb in snares:
            n = int(0.25 * SR)
            tt = np.arange(n) / SR
            noise = rng.standard_normal(n)
            noise = biquad_hp(noise, 1800) * np.exp(-tt * 22)
            tone = np.sin(2 * np.pi * 200 * tt) * np.exp(-tt * 30) * 0.4
            add(buf, (noise * 0.35 + tone) * (0.58 if hard else 0.38), t_of(bar, sb))
    hat_div = 8 if hard or build else 4
    for h in range(hat_div):
        if soft and h % 2 == 1:
            continue
        n = int(0.08 * SR)
        tt = np.arange(n) / SR
        noise = rng.standard_normal(n)
        noise = biquad_hp(noise, 7000) * np.exp(-tt * 60)
        amp = 0.22 if hard else 0.12
        acc = 1.0 if h % 2 == 0 else 0.6
        add(buf, noise * amp * acc, t_of(bar, h * 4.0 / hat_div))
    if bar in (32, 40):
        n = int(1.8 * SR)
        tt = np.arange(n) / SR
        noise = rng.standard_normal(n)
        noise = biquad_hp(noise, 4000) * np.exp(-tt * 2.5)
        add(buf, noise * 0.26, t_of(bar))

def voice_perc(buf, bar):
    sec = section_of(bar)
    if sec == "intro" or (sec == "verse" and bar < 10):
        return
    for s in range(8):
        if s % 2 == 1 and sec == "verse" and bar < 16:
            continue
        n = int(0.06 * SR)
        tt = np.arange(n) / SR
        noise = rng.standard_normal(n)
        noise = biquad_hp(noise, 5500) * np.exp(-tt * 70)
        amp = 0.1 if sec in ("chorus", "build") else 0.06
        if sec == "outro":
            amp = 0.04
        add(buf, noise * amp, t_of(bar, s * 0.5))
    if sec == "build" and bar % 2 == 1:
        n = int(0.3 * SR)
        tt = np.arange(n) / SR
        f = 180 * np.exp(-tt * 12) + 90
        phase = 2 * np.pi * np.cumsum(f) / SR
        add(buf, np.sin(phase) * np.exp(-tt * 10) * 0.22, t_of(bar, 3.5))

def voice_backing(buf, bar):
    root, quality, bass = cell(bar)
    sec = section_of(bar)
    if bar < 6:
        return
    if sec == "intro" and bar < 6:
        return
    notes = chord_midis(root, quality, 1)
    n = int(BAR * SR)
    tt = np.arange(n) / SR
    level = 0.05
    if sec == "verse":
        level = 0.055
    if sec == "build":
        level = 0.075
    if sec == "chorus":
        level = 0.095
    if sec == "outro":
        level = 0.05
    env = env_adsr(n, 1.0, 0.5, 0.7, 1.2)
    sig = np.zeros(n)
    for m in notes[:3]:
        f = midi_hz(m + 12)
        sig += np.sin(2 * np.pi * f * tt) * 0.5
        sig += np.sin(2 * np.pi * f * 2 * tt) * 0.15
        sig += 0.08 * np.sin(2 * np.pi * 350 * tt) * np.sin(2 * np.pi * f * tt)
        sig += 0.05 * np.sin(2 * np.pi * 800 * tt) * np.sin(2 * np.pi * f * 2 * tt)
        breath = rng.standard_normal(n) * 0.004
        sig += biquad_lp(breath, 2500)
    sig = biquad_lp(sig, 4500, 0.8)
    add(buf, sig * env * level / 3, t_of(bar))

def voice_fx(buf):
    # Render bed and events separately so riser peaks don't crush the surf.
    bed = np.zeros(N, dtype=np.float64)
    events = np.zeros(N, dtype=np.float64)
    noise = rng.standard_normal(N)
    brown = np.cumsum(noise)
    brown /= np.max(np.abs(brown)) + 1e-9
    tt = np.arange(N) / SR
    wave_lfo = 0.45 + 0.55 * (0.5 + 0.5 * np.sin(2 * np.pi * tt / 4.7))
    wave_lfo *= 0.55 + 0.45 * np.sin(2 * np.pi * tt / 7.3 + 1.0)
    surf = biquad_lp(brown, 900, 0.7)
    surf = biquad_hp(surf, 80)
    ocean = surf * wave_lfo
    ocean *= 0.55 + 0.45 * (0.5 + 0.5 * np.sin(2 * np.pi * tt / DUR))
    # no broadband foam — brown surf only (kills the strange hiss)
    bed += ocean * 40.0
    rms = float(np.sqrt(np.mean(bed ** 2))) + 1e-12
    bed *= 0.05 / rms
    bed = biquad_lp(bed, 2200, 0.7)
    bed = biquad_hp(bed, 60, 0.7)
    bed = np.tanh(bed * 1.05)
    add(buf, bed, 0)

    # soft air only at chorus peak; band-limited, low level
    air = biquad_hp(biquad_lp(noise, 6000, 0.7), 3500) * 0.004
    for bar in range(32, 48):
        n = int(BAR * SR)
        i0 = idx(t_of(bar))
        seg = air[i0: i0 + n]
        if len(seg) < n:
            seg = np.pad(seg, (0, n - len(seg)))
        env = env_adsr(n, 0.5, 0.5, 0.6, 1.0)
        add(buf, seg * env, t_of(bar))

    def riser_at(bar, amp_sine, amp_noise, length_bars=2):
        n = int(length_bars * BAR * SR)
        tloc = np.arange(n) / SR
        f0, f1 = 200, 2400
        f = f0 * (f1 / f0) ** (tloc / (length_bars * BAR))
        phase = 2 * np.pi * np.cumsum(f) / SR
        r = np.sin(phase) * amp_sine
        r += biquad_hp(rng.standard_normal(n), 3000) * amp_noise * (tloc / (length_bars * BAR))
        add(buf, r * np.linspace(0, 1, n) ** 1.5, t_of(bar))

    riser_at(30, 0.05, 0.03)
    riser_at(38, 0.04, 0.025)
    n = int(BAR * SR)
    tloc = np.arange(n) / SR
    f = 1800 * (80 / 1800) ** (tloc / BAR)
    phase = 2 * np.pi * np.cumsum(f) / SR
    add(buf, np.sin(phase) * np.exp(-tloc * 1.2) * 0.07, t_of(52))

# soft-knee peak normalize that keeps relative dynamics
def normalize_peak(buf, target=0.89):
    peak = float(np.max(np.abs(buf)))
    if peak < 1e-6:
        return buf
    # don't crush quiet stems to silence: scale then only tanh if over
    buf = buf * (target / peak)
    return buf

def render_stem(name):
    buf = np.zeros(N, dtype=np.float64)
    for bar in range(N_BARS):
        if name == "Keyboard":
            voice_keyboard(buf, bar)
        elif name == "Bass":
            voice_bass(buf, bar)
        elif name == "Strings":
            voice_strings(buf, bar)
        elif name == "Synth":
            voice_synth(buf, bar)
        elif name == "Brass":
            voice_brass(buf, bar)
        elif name == "Woodwinds":
            voice_woodwinds(buf, bar)
        elif name == "Drums":
            voice_drums(buf, bar)
        elif name == "Percussion":
            voice_perc(buf, bar)
        elif name == "Backing_Vocals":
            voice_backing(buf, bar)
        elif name == "FX":
            if bar == 0:
                voice_fx(buf)
    buf = normalize_peak(buf, 0.89)
    buf = np.tanh(buf * 1.15) * 0.92
    # gate residual noise floor so silent-ish stems don't hiss after boost
    win = int(0.03 * SR)
    if len(buf) > win:
        pad = (-len(buf)) % win
        chunks = np.pad(buf, (0, pad)).reshape(-1, win)
        rms = np.sqrt(np.mean(chunks ** 2, axis=1) + 1e-12)
        thr = max(0.004, float(np.percentile(rms, 20)) * 0.35)
        mask = rms > thr
        # soft expand below threshold instead of hard cut (avoids clicks)
        gain = np.ones_like(rms)
        below = ~mask
        gain[below] = np.clip(rms[below] / thr, 0.0, 1.0) ** 2
        gains_f = np.repeat(gain, win)[: len(buf)]
        buf = buf * gains_f
    return buf.astype(np.float32)

def write_wav(path, data):
    d = np.clip(data, -1, 1)
    pcm = (d * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())

def main():
    print(f"Oceans v2: {N_BARS} bars, {DUR:.1f}s, {N} samples @ {SR}Hz, {BPM}BPM")
    print("Progressions: intro/verse Bm-A/C#-D-A-G | chorus G-D-A-Bm")
    mix = np.zeros(N, dtype=np.float32)
    gains = {
        "Backing_Vocals": 1.0, "Drums": 1.1, "Bass": 1.1, "Keyboard": 1.15,
        "Percussion": 0.9, "Strings": 1.0, "Synth": 1.0, "FX": 1.15,
        "Brass": 1.0, "Woodwinds": 0.85,
    }
    for name in STEMS:
        print(f"  rendering {name}...")
        data = render_stem(name)
        path = os.path.join(WAVS, f"{name}.wav")
        write_wav(path, data)
        mix += data * gains[name]
        print(f"    peak={np.max(np.abs(data)):.3f} -> {path}")
    peak = np.max(np.abs(mix))
    if peak > 1e-6:
        mix = mix * (0.95 / peak)
    write_wav(os.path.join(WAVS, "_mix_ref.wav"), np.tanh(mix * 1.1))
    print(f"DONE. Duration={DUR:.2f}s files in {WAVS}")

if __name__ == "__main__":
    main()
