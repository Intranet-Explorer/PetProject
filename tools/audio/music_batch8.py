"""Batch 8: music for places and moods. Same toolkit/mastering as batches 0-1:
voices rendered with release tails into an L+tail buffer, tail folded into the start (seamless loop),
rotated to the upward zero crossing nearest the downbeat + 32-sample taper, -20 LUFS, <= -1 dBTP.
Every piece keeps a legato/sustained layer (bass and/or pad) under the tune, so note boundaries never
open level gaps (check.py 'dips'). Stereo pieces: dry voices centred/lightly panned (linear pan, mono
sum unchanged) + ping-pong echo taps (as batch 1). Others mono to keep files small."""
import sys
from synth import *
import synth as S
from music_batch1 import Song2, mel, chords_to_arp, pingpong, master_st
from music import vib
OUT = '/workspace/house-audio/music'
def seed(s): S.rng = np.random.default_rng(s)
def R(): return S.rng

# ------------------------------------------------------------------ instruments (f, d, gate, t0)
def P(duty=0.25, lpf=3200, dep=0.15, rate=5.2, a=0.012, dk=0.2, sus=0.62, rel=0.2):
    def f_(f, d, g, t0):
        n = N(d + rel); x = pulse(vib(f, n, dep, rate, 0.18, 0.2), n / SR, duty)
        return lp(x, lpf) * adsr(n, a, dk, sus, rel, N(g))
    return f_
def T(lpf=3000, dep=0.12, rate=5.0, a=0.02, dk=0.3, sus=0.7, rel=0.3, steps=True):
    def f_(f, d, g, t0):
        n = N(d + rel); x = tri(vib(f, n, dep, rate, 0.2, 0.3), n / SR, steps)
        return lp(x, lpf) * adsr(n, a, dk, sus, rel, N(g))
    return f_
def BOX(tau=0.45, lpf=4000):
    def f_(f, d, g, t0):
        n = N(d + 0.8); return lp(tri(f, n / SR), lpf) * expenv(n, tau, 0.003)
    return f_
def PAD(lpf=1300, a=0.25, rel=0.6, wave='tri'):
    def f_(f, d, g, t0):
        n = N(d + rel); tt = np.arange(n) / SR
        fr = f * 2 ** (0.04 * np.sin(2 * np.pi * 0.35 * tt + f) / 12)
        x = tri(fr, n / SR, steps=False) if wave == 'tri' else pulse(fr, n / SR, 0.5) * 0.6
        return lp(x, lpf) * adsr(n, a, 0.4, 0.8, rel, N(g))
    return f_
def BASS(lpf=1500, a=0.015, rel=0.08):
    def f_(f, d, g, t0):
        n = N(d + rel); return lp(tri(f, n / SR), lpf) * adsr(n, a, 0.25, 0.8, rel, N(g))
    return f_
def PB(duty=0.5, lpf=900, rel=0.06):        # pulse bass (busy pieces), legato
    def f_(f, d, g, t0):
        n = N(d + rel); return lp(pulse(f, n / SR, duty), lpf) * adsr(n, 0.005, 0.12, 0.65, rel, N(g))
    return f_
def BELL(tau=0.5):
    def f_(f, d, g, t0):
        n = N(d + 1.2); t = np.arange(n) / SR; y = np.zeros(n)
        for r, am, tr in [(1, 1, tau), (2, 0.3, tau * 0.5), (2.76, 0.18, tau * 0.35), (5.4, 0.06, tau * 0.2)]:
            y += am * np.sin(2 * np.pi * f * r * t) * np.exp(-t / tr)
        return lp(y * np.minimum(t / 0.002, 1), 6000)
    return f_

# ------------------------------------------------------------------ drums (soft, warm)
def kit():
    def kick(): d = 0.18; return tri(expsweep(130, 45, d), d, steps=False) * expenv(N(d), 0.07, 0.002)
    def snare():
        d = 0.16; n = N(d)
        return 0.6 * bp(R().normal(0, 1, n), 900, 5000) * expenv(n, 0.045, 0.001) + 0.35 * tri(expsweep(230, 170, d), d) * expenv(n, 0.03, 0.001)
    def hat(): d = 0.04; n = N(d); return bp(R().normal(0, 1, n), 4000, 8500) * expenv(n, 0.01, 0.0005)
    def shk(): d = 0.06; n = N(d); return bp(R().normal(0, 1, n), 2500, 6000) * adsr(n, 0.01, 0.02, 0.4, 0.02, N(0.03))
    def tom(): d = 0.25; return tri(expsweep(180, 95, d), d, steps=False) * expenv(N(d), 0.08, 0.002)
    def ltom(): d = 0.35; return tri(expsweep(110, 55, d), d, steps=False) * expenv(N(d), 0.14, 0.003)
    def blk(): d = 0.06; return tri(expsweep(900, 780, d), d, steps=False) * expenv(N(d), 0.012, 0.0005)
    def tink(): d = 0.25; t = np.arange(N(d)) / SR; return (np.sin(2 * np.pi * 1760 * t) * np.exp(-t / 0.05) + 0.4 * np.sin(2 * np.pi * 4100 * t) * np.exp(-t / 0.02))
    def jingle():
        d = 0.18; n = N(d); y = np.zeros(n)
        for _ in range(7): place(y, bp(R().normal(0, 1, N(0.03)), 5000, 9000) * expenv(N(0.03), 0.006, 0.0005), N(R().uniform(0, 0.06)), R().uniform(0.3, 1))
        t = np.arange(n) / SR
        for f in R().uniform(2600, 3600, 3): y += 0.15 * np.sin(2 * np.pi * f * t) * np.exp(-t / 0.04)
        return lp(y, 8000)
    return dict(k=kick, s=snare, h=hat, z=shk, t=tom, l=ltom, b=blk, i=tink, j=jingle)
def drums(s, bars, gains):
    out = s.buf(); K = kit()
    for b, pat in enumerate(bars):
        if not pat: continue
        for name, row in pat.items():
            for i, ch in enumerate(row):
                if ch in 'xo': place(out, K[name](), s.ts(b * s.spb + i), gains[name] * (1 if ch == 'x' else 0.5))
    return out

# ------------------------------------------------------------------ helpers
def pad_chords(s, chords, inst, bars_per=1, gain=1.0, start=0):
    out = s.buf()
    for i, c in enumerate(chords):
        for nm in c.split(): s.line([(midi(nm), s.spb * bars_per)], inst, start + i * bars_per, gain, out=out, gate=1.0)
    return out
def bass_line(s, roots, pattern, inst, gate=1.0):
    """pattern: list of (interval, steps) per bar applied to each root."""
    nl = []
    for r in roots: nl += [(midi(r) + iv, st) for iv, st in pattern]
    return s.line(nl, inst, 0, 1.0, gate=gate)
def bar_gain(s, x, gains, ramp=0.25):
    """Per-bar gain curve (smoothed) for arrangement dynamics; wraps around the loop."""
    L = s.L; per = L / len(gains); g = np.repeat(gains, int(np.ceil(per)))[:L] if False else np.interp(np.arange(L), (np.arange(len(gains)) * per), gains)
    g = np.array([gains[int(i // per)] for i in range(0, L, 64)]); g = np.repeat(g, 64)[:L]
    k = max(1, N(ramp)); g = np.convolve(np.concatenate([g[-k:], g, g[:k]]), np.ones(k) / k, 'same')[k:-k]
    full = np.concatenate([g, np.full(len(x) - L, g[0])]); return x * full
def master_mono(s, tracks, target=-20.0):
    mix = hp(lp(sum(tracks), 12000), 25)
    y = mix[:s.L].copy(); t = mix[s.L:]; y[:len(t)] += t
    y, _ = loop_finalize(y, near=0); return level(y, target)
def M(txt, bars, spb=16, oct=0):
    return [(None if n is None else n + 12 * oct, st) for n, st in mel(txt, bars, spb)]

# ================================================================== nursery
def nursery():
    """F major music-box lullaby, 3/4, 69 BPM, 32 bars (A B A' B'). ~83 s, mono."""
    s = Song2(69, 32, spb=12, tail=8.0)
    A = ['F4 A4 C5', 'C4 E4 G4', 'D4 F4 A4', 'Bb3 D4 F4', 'F4 A4 C5', 'G3 Bb3 D4', 'C4 E4 G4', 'F4 A4 C5']
    B = ['Bb3 D4 F4', 'F4 A4 C5', 'G3 Bb3 D4', 'D4 F4 A4', 'Bb3 D4 F4', 'F4 A4 C5', 'C4 E4 G4', 'C4 E4 Bb4']
    B2 = B[:7] + ['F4 A4 C5']
    chords = A + B + A + B2
    roots = ['F2', 'C2', 'D2', 'Bb1', 'F2', 'G1', 'C2', 'F2', 'Bb1', 'F2', 'G1', 'D2', 'Bb1', 'F2', 'C2', 'C2']
    roots = roots + roots[:15] + ['F2']
    mA = "A4:6 C5:2 F5:4  E5:8 C5:4  D5:6 E5:2 F5:4  D5:12  C5:6 F5:2 A5:4  G5:6 F5:2 D5:4  E5:4 G5:4 E5:4  F5:12"
    mB = "D5:6 F5:2 Bb5:4  A5:8 F5:4  G5:6 A5:2 Bb5:4  A5:12  F5:6 D5:2 Bb4:4  C5:6 A4:2 F5:4  E5:4 D5:4 C5:4  C5:8 R:4"
    mB2 = mB.rsplit("E5:4 D5:4 C5:4  C5:8 R:4", 1)[0] + "E5:4 G5:4 E5:4  F5:12"
    box = BOX(0.5); m = s.buf()
    for t_, bar in [(mA, 0), (mB, 8), (mA, 16), (mB2, 24)]: s.line(M(t_, 8, 12), box, bar, 1.0, out=m)
    hi = s.buf()                                          # second half: the tune doubled softly an octave up
    for t_, bar in [(mA, 16), (mB2, 24)]: s.line(M(t_, 8, 12, 1), BOX(0.35, 5000), bar, 1.0, out=hi)
    ar = s.line(chords_to_arp(chords, [0, 1, 2, 3, 2, 1], 12, 2), BOX(0.35, 3500), 0, 1.0)
    cm = s.buf()                                          # B sections: soft pulse counter-line (long notes)
    for bar, t_ in [(8, "F4:12 F4:12 D4:12 F4:12 F4:12 C4:12 C4:12 E4:12"), (24, "F4:12 F4:12 D4:12 F4:12 F4:12 C4:12 C4:12 C4:12")]:
        s.line(M(t_, 8, 12), P(0.125, 1800, 0.1, 4.5, 0.08, 0.3, 0.6, 0.3), bar, 1.0, out=cm)
    pd = pad_chords(s, chords, PAD(1000, 0.3, 0.6))
    bs = s.line([(midi(r) + 12, 12) for r in roots], BASS(900, 0.04, 0.3), 0, 1.0, gate=1.0)
    y = master_mono(s, [delay(m, 4 * s.step, fb=0.3, mix=0.3, damp=2500) * 0.5, hi * 0.12, ar * 0.2, cm * 0.1, pd * 0.07, bs * 0.4])
    return y, dict(key='F major', bpm=69, meter='3/4', bars=32, form='A B A\' B\'')

# ================================================================== pond
def pond():
    """C lydian (C major with F#), 76 BPM, 24 bars (A B A'). Floaty triangle tune with slow vibrato,
    rippling 12.5% pulse arpeggios in ping-pong echo, water-drop plinks, long bass. ~76 s, stereo."""
    s = Song2(76, 24, tail=8.0)
    A = ['C4 E4 G4 B4', 'C4 D4 F#4 A4', 'C4 E4 G4 B4', 'C4 D4 F#4 A4', 'A3 C4 E4 G4', 'B3 D4 F#4 A4', 'E4 G4 B4 D5', 'D4 F#4 A4 C5']
    B = ['A3 C4 E4 G4', 'D4 F#4 A4 C5', 'G3 B3 D4 F#4', 'C4 E4 G4 B4', 'A3 C4 E4 G4', 'D4 F#4 A4 C5', 'E4 G4 B4 D5', 'D4 F#4 A4 C5']
    chords = A + B + A
    roots = ['C2', 'C2', 'C2', 'C2', 'A1', 'B1', 'E2', 'D2', 'A1', 'D2', 'G1', 'C2', 'A1', 'D2', 'E2', 'D2', 'C2', 'C2', 'C2', 'C2', 'A1', 'B1', 'E2', 'D2']
    mA = ("E5:8 G5:4 B5:4  A5:8 F#5:4 D5:4  E5:6 G5:2 B5:4 C6:4  A5:12 R:4  "
          "C6:6 B5:2 A5:4 E5:4  F#5:8 D5:4 B4:4  G5:6 F#5:2 E5:4 D5:4  F#5:12 R:4")
    mB = ("A4:4 C5:4 E5:4 G5:4  F#5:8 A5:8  B5:6 A5:2 G5:4 D5:4  E5:16  "
          "A5:4 G5:4 E5:4 C5:4  D5:8 F#5:4 A5:4  G5:8 B5:4 E6:4  D6:12 R:4")
    mA2 = mA.rsplit("F#5:12 R:4", 1)[0] + "D5:4 E5:4 F#5:4 A5:4"
    lead = T(3200, 0.2, 4.2, 0.04, 0.4, 0.7, 0.4, steps=False)
    m = s.buf()
    for t_, bar in [(mA, 0), (mB, 8), (mA2, 16)]: s.line(M(t_, 8), lead, bar, 1.0, out=m)
    ar = s.line(chords_to_arp(chords, [0, 1, 2, 3, 4, 3, 2, 1], 16, 2), P(0.125, 3000, 0, 5, 0.004, 0.1, 0.25, 0.08), 0, 1.0, gate=0.7)
    pd = pad_chords(s, chords, PAD(1100, 0.4, 0.8))
    bs = s.line([(midi(r) + 12, 16) for r in roots], BASS(800, 0.15, 0.5), 0, 1.0, gate=1.0)
    dr = s.buf(); pent = ['G5', 'A5', 'B5', 'D6', 'E6', 'F#6']
    for bar in range(24):                                  # water-drop plinks (rising sine chirps), 1-2 per bar
        for _ in range(int(R().integers(1, 3))):
            f = fq(R().choice(pent)); d = 0.05; n = N(d); tt = np.arange(n) / SR
            x = np.sin(2 * np.pi * np.cumsum(expsweep(f * 0.8, f, d)) / SR) * np.exp(-tt / 0.015)
            place(dr, x, s.ts(bar * 16 + int(R().choice([2, 5, 7, 10, 13, 15]))), R().uniform(0.5, 1))
    eL, eR = pingpong(m * 0.45 + ar * 0.22 + dr * 0.1, 3 * s.step * 2, fb=0.45, mix=0.5, damp=2200, width=0.9)
    y = master_st(s, [(m * 0.45, 0), (ar * 0.22, -0.3), (pd * 0.08, 0), (bs * 0.45, 0), (dr * 0.1, 0.3)], eL, eR)
    return y, dict(key='C lydian', bpm=76, meter='4/4', bars=24, form='A B A\'')

# ================================================================== cellar
def cellar():
    """D minor, 56 BPM, 16 bars (A B). Low and dim: low-register muted pulse tune, slow triangle bass
    walking in half notes, dark pad, soft heartbeat kick, rare drips. ~69 s, mono."""
    s = Song2(56, 16, tail=8.0)
    ch = ['D3 F3 A3', 'Bb2 D3 F3', 'G2 Bb2 D3', 'A2 C#3 E3', 'D3 F3 A3', 'F2 A2 C3', 'G2 Bb2 D3', 'A2 C#3 G3']
    chords = ch + ch
    roots = ['D2', 'Bb1', 'G1', 'A1', 'D2', 'F1', 'G1', 'A1'] * 2
    mA = ("D4:8 F4:4 E4:4  D4:12 R:4  G4:8 Bb4:4 A4:4  A4:12 R:4  "
          "D4:6 E4:2 F4:4 A4:4  C5:8 A4:8  Bb4:6 A4:2 G4:4 F4:4  E4:12 R:4")
    mB = ("R:8 A3:8  Bb3:8 D4:8  G3:12 R:4  C#4:8 E4:8  "
          "F4:8 E4:4 D4:4  C4:8 A3:8  Bb3:4 D4:4 G4:4 F4:4  E4:8 C#4:8")
    m = s.buf(); lead = P(0.5, 1300, 0.1, 4.5, 0.05, 0.4, 0.6, 0.4)
    s.line(M(mA, 8), lead, 0, 1.0, out=m); s.line(M(mB, 8), T(1500, 0.1, 4.5, 0.05, 0.4, 0.7, 0.4), 8, 1.0, out=m)
    pd = pad_chords(s, chords, PAD(700, 0.8, 1.0))
    bs = bass_line(s, roots, [(0, 8), (7, 8)], BASS(500, 0.05, 0.25))
    hb = drums(s, [{'l': 'x.....o.........'}] * 16, {'l': 0.35})
    dp = s.buf()
    for bar in range(1, 16, 3):
        f = fq(R().choice(['A5', 'D6', 'F5'])); n = N(0.06); tt = np.arange(n) / SR
        place(dp, np.sin(2 * np.pi * np.cumsum(expsweep(f * 0.7, f, 0.06)) / SR) * np.exp(-tt / 0.012), s.ts(bar * 16 + int(R().integers(3, 14))), 1.0)
    y = master_mono(s, [delay(m, 6 * s.step, fb=0.35, mix=0.35, damp=1200) * 0.5, pd * 0.12, bs * 0.55, hb, delay(dp, 0.31, fb=0.4, mix=0.5, damp=2000) * 0.05])
    return y, dict(key='D minor', bpm=56, meter='4/4', bars=16, form='A B')

# ================================================================== workshop
def workshop():
    """C major, 112 BPM, 40 bars (groove, A, B, A', B'). Busy: bouncy pulse bass, wood-block and
    soft anvil-tink 'tool' percussion, shaker, call-and-response square lead opening with the
    house motif (E-G-A-G), triangle answers. ~86 s, mono (also for the machine room)."""
    s = Song2(112, 40, tail=6.0)
    A = ['C4 E4 G4', 'F4 A4 C5', 'G3 B3 D4', 'C4 E4 G4', 'A3 C4 E4', 'F3 A3 C4', 'D4 F#4 C5', 'G3 B3 D4']
    B = ['F3 A3 C4', 'G3 B3 D4', 'E3 G3 B3', 'A3 C4 E4', 'D4 F4 A4', 'G3 B3 F4', 'C4 E4 G4', 'G3 B3 D4']
    chords = A + A + B + A + B
    rA = ['C2', 'F2', 'G1', 'C2', 'A1', 'F1', 'D2', 'G1']; rB = ['F1', 'G1', 'E2', 'A1', 'D2', 'G1', 'C2', 'G1']
    roots = rA + rA + rB + rA + rB
    mA = ("E5:3 G5:1 A5:2 G5:2 E5:2 R:2 C5:2 D5:2  F5:2 R:2 A5:2 R:2 C6:2 A5:2 F5:4  "
          "G5:3 A5:1 B5:2 G5:2 D5:2 R:2 B4:2 D5:2  E5:2 R:2 C5:2 R:2 G4:4 R:4  "
          "A4:2 C5:2 E5:2 A5:2 G5:2 E5:2 C5:2 E5:2  F5:2 A5:2 C6:2 A5:2 F5:4 R:4  "
          "F#5:2 A5:2 D6:2 C6:2 A5:2 F#5:2 D5:4  G5:4 B5:4 D6:4 R:4")
    mB = ("A5:4 G5:2 F5:2 C5:4 F5:4  G5:4 F5:2 E5:2 D5:4 B4:4  E5:2 G5:2 B5:2 G5:2 E5:4 R:4  "
          "A5:2 C6:2 E6:2 C6:2 A5:4 R:4  D5:2 F5:2 A5:2 F5:2 D5:2 F5:2 A5:2 C6:2  B5:4 G5:2 F5:2 D5:4 R:4  "
          "E5:3 G5:1 A5:2 G5:2 E5:2 D5:2 C5:4  D5:2 R:2 G5:2 R:2 B4:4 R:4")
    lead = P(0.25, 3000, 0.08, 6, 0.005, 0.12, 0.55, 0.06)
    m = s.buf()
    for t_, bar in [(mA, 8), (mB, 16), (mA, 24), (mB, 32)]: s.line(M(t_, 8), lead, bar, 1.0, out=m, gate=0.8)
    # triangle answers: echo the last phrase of each 2 bars an octave lower in the gaps (A' / B' only)
    ans = s.buf()
    for bar in (24, 26, 28, 30, 32, 34, 36, 38):
        ch = chords[bar + 1].split(); s.line([(None, 8), (midi(ch[0]), 2), (midi(ch[1]), 2), (midi(ch[2]), 4)], T(2500, 0, 5, 0.005, 0.1, 0.6, 0.06), bar + 1, 1.0, out=ans, gate=0.8)
    ar = s.line(chords_to_arp(chords, [0, 2, 1, 2], 16, 2), P(0.125, 2500, 0, 5, 0.003, 0.08, 0.3, 0.05), 0, 1.0, gate=0.6)
    bs = bass_line(s, roots, [(12, 2), (24, 2), (19, 2), (24, 2), (12, 2), (24, 2), (19, 2), (22 - 3, 2)], PB(0.5, 900), gate=1.0)
    pd = pad_chords(s, chords, PAD(900, 0.1, 0.3))
    g0 = {'k': 'x.......x.......', 'b': '..x...x...x.x...', 'z': 'o.o.o.o.o.o.o.o.'}
    g1 = {'k': 'x.......x.......', 's': '....o.......o...', 'b': '..x...x...x.x...', 'z': 'oooooooooooooooo', 'i': '............x...'}
    g2 = {'k': 'x.....x.x.......', 's': '....o.......o..o', 'b': '..x..x....x.x...', 'z': 'oooooooooooooooo', 'i': '......x.........'}
    bars = [g0] * 8 + [g1, g1, g1, g2] * 8
    dr = drums(s, bars, {'k': 0.4, 's': 0.12, 'b': 0.12, 'z': 0.05, 'i': 0.04})
    y = master_mono(s, [delay(m, 3 * s.step, fb=0.25, mix=0.25, damp=2500) * 0.42, ans * 0.25, ar * 0.13, bs * 0.4, pd * 0.06, dr * 0.8])
    return y, dict(key='C major', bpm=112, meter='4/4', bars=40, form='groove A B A\' B\'')

# ================================================================== tension
def tension():
    """E minor, 96 BPM, 32 bars. A quarrel building: two voices bicker (square high vs triangle low,
    call and answer), over a half-step ostinato (E-E-F-E); B: exchanges shorten and climb; C: both
    voices together, full drums; D: ostinato + low tom roll subsides back to the start. ~80 s, mono."""
    s = Song2(96, 32, tail=6.0)
    chA = ['E3', 'E3', 'C3', 'B2'] * 2; chB = ['A2', 'E3', 'A2', 'B2', 'C3', 'G2', 'A2', 'B2']
    chC = ['E3', 'G2', 'A2', 'B2', 'E3', 'B2', 'A2', 'B2']; chD = ['E3', 'E3', 'C3', 'B2', 'E3', 'E3', 'C3', 'B2']
    roots = chA + chB + chC + chD
    ost = []
    for r in roots: mm = midi(r); ost += [(mm, 2), (mm, 2), (mm + 1, 2), (mm, 2)] * 2
    o = s.line(ost, P(0.125, 1600, 0, 5, 0.004, 0.08, 0.45, 0.05), 0, 1.0, gate=0.75)
    hi = ("B4:2 C5:2 B4:2 R:2 G4:2 A4:2 B4:4  R:16  B4:2 C5:2 D5:2 R:2 C5:2 B4:2 A4:4  R:16  "
          "E5:2 F#5:2 G5:2 R:2 F#5:2 E5:2 D#5:4  R:16  E5:2 G5:2 B5:4 A5:2 G5:2 F#5:4  D#5:8 R:8")
    lo = ("R:16  E4:2 D4:2 E4:2 R:2 G4:2 F#4:2 E4:4  R:16  A3:2 B3:2 C4:2 R:2 B3:2 A3:2 B3:4  "
          "R:16  C4:2 B3:2 A3:2 R:2 B3:2 C4:2 B3:4  R:16  B3:8 R:8")
    hiB = ("A4:2 C5:2 E5:4 R:8  B4:2 E5:2 G5:4 R:8  C5:2 E5:2 A5:4 R:8  D#5:2 F#5:2 B5:4 R:8  "
           "E5:2 G5:2 C6:4 R:8  D5:2 G5:2 B5:4 R:8  E5:2 A5:2 C6:4 R:8  F#5:2 A5:2 B5:2 D#6:2 R:8")
    loB = ("R:8 A4:2 E4:2 C4:4  R:8 G4:2 E4:2 B3:4  R:8 A4:2 E4:2 C4:4  R:8 B4:2 F#4:2 D#4:4  "
           "R:8 C5:2 G4:2 E4:4  R:8 B4:2 G4:2 D4:4  R:8 C5:2 A4:2 E4:4  R:8 B4:2 A4:2 F#4:4")
    uni = ("E5:4 E5:2 F#5:2 G5:4 A5:4  B5:8 A5:4 G5:4  C6:4 B5:2 A5:2 G5:4 E5:4  F#5:12 R:4  "
           "E5:4 G5:4 B5:4 E6:4  D#6:8 B5:8  C6:4 A5:4 F#5:4 D#5:4  B4:12 R:4")
    sq = P(0.25, 2800, 0.12, 6, 0.006, 0.15, 0.6, 0.08); tr = T(2400, 0.1, 6, 0.006, 0.15, 0.75, 0.08)
    m = s.buf(); l2 = s.buf()
    s.line(M(hi, 8), sq, 0, 1.0, out=m, gate=0.85); s.line(M(lo, 8), tr, 0, 1.0, out=l2, gate=0.85)
    s.line(M(hiB, 8), sq, 8, 1.0, out=m, gate=0.85); s.line(M(loB, 8), tr, 8, 1.0, out=l2, gate=0.85)
    s.line(M(uni, 8), sq, 16, 1.0, out=m, gate=0.9); s.line(M(uni, 8, oct=-1), tr, 16, 1.0, out=l2, gate=0.9)
    bs = s.line([(midi(r), 16) for r in roots], BASS(700, 0.02, 0.15), 0, 1.0, gate=1.0)
    pd = pad_chords(s, [{'E3': 'E3 G3 B3', 'C3': 'C3 E3 G3', 'B2': 'B2 D#3 F#3', 'A2': 'A2 C3 E3', 'G2': 'G2 B2 D3'}[r] for r in roots], PAD(900, 0.2, 0.4))
    dA = {'k': 'x...............'}; dB = {'k': 'x.......x.......', 's': '............o...'}
    dC = {'k': 'x.......x.x.....', 's': '....x.......x...', 'h': 'o.o.o.o.o.o.o.o.'}; dCf = dict(dC, t='........x.x.x.x.')
    dD = {'k': 'x.......o.......'}; dDr = {'k': 'x.......', 'l': '........o.o.oooo'}
    bars = [dA] * 8 + [dB] * 7 + [dict(dB, t='............x.x.')] + [dC] * 7 + [dCf] + [dD] * 7 + [dDr]
    dr = drums(s, bars, {'k': 0.4, 's': 0.14, 'h': 0.035, 't': 0.25, 'l': 0.3})
    dyn = [0.75] * 8 + [0.85 + 0.02 * i for i in range(8)] + [1.0] * 8 + [0.95 - 0.025 * i for i in range(8)]
    mix_ = [m * 0.38, l2 * 0.3, o * 0.13, bs * 0.45, pd * 0.06, dr * 0.75]
    y = master_mono(s, [bar_gain(s, x, dyn) for x in mix_])
    return y, dict(key='E minor', bpm=96, meter='4/4', bars=32, form='A (bicker) B (climb) C (together) D (subside)')

# ================================================================== fight
def fight():
    """D minor, 140 BPM, 40 bars (A B A C A+harmony). Cartoon-dramatic: driving pulse bass in 8ths,
    backbeat, heroic minor riff, B lifts to F major, C bridge with Eb (Neapolitan colour) and tom fills,
    chord stabs. Warm low-passed voices, no harsh highs. ~69 s, mono."""
    s = Song2(140, 40, tail=5.0)
    rA = ['D2', 'D2', 'Bb1', 'C2', 'D2', 'D2', 'Bb1', 'A1']; rB = ['F2', 'C2', 'D2', 'A1', 'Bb1', 'C2', 'D2', 'A1']
    rC = ['G1', 'G1', 'D2', 'D2', 'Eb2', 'Eb2', 'A1', 'A1']
    roots = rA + rB + rA + rC + rA
    q = {'D': 'D3 F3 A3', 'Bb': 'Bb2 D3 F3', 'C': 'C3 E3 G3', 'A': 'A2 C#3 E3', 'F': 'F3 A3 C4', 'G': 'G2 Bb2 D3', 'Eb': 'Eb3 G3 Bb3'}
    chords = [q[r[:-1]] for r in roots]
    mA = ("D5:2 D5:2 F5:2 D5:2 A5:4 G5:2 F5:2  E5:2 F5:2 G5:4 F5:4 E5:4  D5:2 F5:2 Bb5:4 A5:2 G5:2 F5:4  "
          "E5:2 G5:2 C6:4 Bb5:2 A5:2 G5:4  D5:2 D5:2 F5:2 D5:2 A5:4 G5:2 F5:2  E5:2 F5:2 G5:4 A5:4 Bb5:4  "
          "A5:4 F5:4 D5:4 F5:4  E5:8 C#5:8")
    mB = ("A5:6 G5:2 F5:4 C5:4  G5:6 F5:2 E5:4 C5:4  F5:4 A5:4 D6:4 C6:4  C#6:8 A5:8  "
          "Bb5:6 A5:2 G5:4 D5:4  C6:6 Bb5:2 A5:4 E5:4  F5:4 E5:4 D5:4 F5:4  E5:4 A5:4 C#6:4 E5:4")
    mC = ("G4:4 Bb4:4 D5:4 G5:4  F5:4 D5:4 Bb4:4 G4:4  A4:4 D5:4 F5:4 A5:4  G5:4 F5:4 E5:4 D5:4  "
          "Eb5:4 G5:4 Bb5:4 G5:4  Eb5:4 Bb4:4 G4:4 Eb4:4  E4:2 A4:2 C#5:2 E5:2 A5:4 E5:4  C#5:4 E5:4 A5:8")
    hA = ("A4:2 A4:2 D5:2 A4:2 F5:4 E5:2 D5:2  C#5:2 D5:2 E5:4 D5:4 C#5:4  Bb4:2 D5:2 F5:4 F5:2 E5:2 D5:4  "
          "C5:2 E5:2 G5:4 G5:2 F5:2 E5:4  A4:2 A4:2 D5:2 A4:2 F5:4 E5:2 D5:2  C#5:2 D5:2 E5:4 F5:4 G5:4  "
          "F5:4 D5:4 A4:4 D5:4  C#5:8 A4:8")
    lead = P(0.25, 3000, 0.1, 6.5, 0.004, 0.12, 0.65, 0.06)
    m = s.buf()
    for t_, bar in [(mA, 0), (mB, 8), (mA, 16), (mC, 24), (mA, 32)]: s.line(M(t_, 8), lead, bar, 1.0, out=m, gate=0.88)
    h = s.line(M(hA, 8), P(0.125, 2500, 0.1, 6.5, 0.004, 0.12, 0.6, 0.06), 32, 1.0, gate=0.88)
    bs = bass_line(s, roots, [(12, 2), (12, 2), (24, 2), (12, 2)] * 2, PB(0.5, 800), gate=1.0)
    st = s.buf()
    for b, c in enumerate(chords):
        for nm in c.split():
            for pos in ((0, 6) if b % 2 == 0 else (0,)):
                s.line([(None, pos), (midi(nm) + 12, 2)], P(0.5, 2000, 0, 5, 0.003, 0.08, 0.4, 0.08), b, 1.0, out=st, gate=0.9)
    pd = pad_chords(s, chords, PAD(900, 0.05, 0.25, 'pulse'))
    g = {'k': 'x.......x.x.....', 's': '....x.......x...', 'h': 'o.o.o.o.o.o.o.o.'}
    fill = {'k': 'x.......x.......', 's': '....x.......x.xo', 't': '........x.x.x.x.', 'h': 'o.o.o.o.'}
    bars = ([g] * 7 + [fill]) * 3 + [dict(g, t='x...........x...')] * 7 + [fill] + [g] * 7 + [fill]
    dr = drums(s, bars, {'k': 0.45, 's': 0.16, 'h': 0.035, 't': 0.25})
    y = master_mono(s, [delay(m, 3 * s.step, fb=0.25, mix=0.2, damp=2500) * 0.4, h * 0.22, bs * 0.38, st * 0.07, pd * 0.04, dr * 0.75])
    return y, dict(key='D minor', bpm=140, meter='4/4', bars=40, form='A B A C(bridge) A+harmony')

# ================================================================== grief
def grief():
    """A minor, 58 BPM, 20 bars (A B coda). After a death: a slow triangle melody built on the house
    motif (E-G-A-G) heard in A minor, soft music-box echoes, warm pad, gentle bass. ~83 s, mono."""
    s = Song2(58, 20, tail=10.0)
    ch = {'Am': 'A3 C4 E4', 'F': 'F3 A3 C4', 'C': 'C4 E4 G4', 'G': 'G3 B3 D4', 'Dm': 'D4 F4 A4', 'E': 'E3 G#3 B3', 'Em': 'E3 G3 B3'}
    prog = ['Am', 'F', 'C', 'G', 'Am', 'F', 'Dm', 'E', 'F', 'G', 'Em', 'Am', 'Dm', 'Am', 'F', 'E', 'Am', 'F', 'Dm', 'E']
    rt = {'Am': 'A1', 'F': 'F1', 'C': 'C2', 'G': 'G1', 'Dm': 'D2', 'E': 'E1', 'Em': 'E2'}
    mA = "E5:12 G5:4  A5:8 G5:8  E5:8 D5:4 C5:4  D5:16  E5:12 G5:4  A5:8 C6:8  B5:8 A5:4 F5:4  G#5:16"
    mB = "A5:8 C6:4 A5:4  G5:8 D5:8  E5:8 G5:4 B5:4  A5:16  F5:8 A5:4 D6:4  C6:8 A5:4 E5:4  F5:8 E5:4 D5:4  E5:16"
    mC = "R:4 E5:4 G5:4 A5:4  A5:8 G5:8  F5:8 D5:8  E5:16"
    lead = T(2600, 0.14, 4.6, 0.08, 0.6, 0.65, 0.6, steps=False)
    m = s.buf()
    for t_, bar, nb in [(mA, 0, 8), (mB, 8, 8), (mC, 16, 4)]: s.line(M(t_, nb), lead, bar, 1.0, out=m, gate=0.95)
    bx = s.buf()                                       # music box answers an octave up, in B only
    s.line(M(mB, 8, oct=1), BOX(0.4, 4500), 8, 1.0, out=bx)
    ar = s.line(chords_to_arp([ch[p] for p in prog], [0, 1, 2, 1], 16, 4), BOX(0.6, 3000), 0, 1.0)
    pd = pad_chords(s, [ch[p] for p in prog], PAD(1000, 0.6, 1.2))
    bs = s.line([(midi(rt[p]) + 12, 16) for p in prog], BASS(600, 0.2, 0.8), 0, 1.0, gate=1.0)
    y = master_mono(s, [delay(m, 6 * s.step, fb=0.35, mix=0.35, damp=1800) * 0.45, bx * 0.08, ar * 0.16, pd * 0.12, bs * 0.4])
    return y, dict(key='A minor', bpm=58, meter='4/4', bars=20, form='A B coda (motif)')

# ================================================================== vengeance
def vengeance():
    """C minor, 80 BPM, 28 bars (intro, A, B, A'). The house motif turned dark: E-G-A-G becomes
    Eb-G-Ab-G in C minor. Low 50% pulse, tolling low triangle bell on each bar, ostinato C-C-Ab-G,
    timpani-like low toms, Db (Neapolitan) colour before the cadence. ~84 s, mono."""
    s = Song2(80, 28, tail=7.0)
    q = {'Cm': 'C3 Eb3 G3', 'Ab': 'Ab2 C3 Eb3', 'Fm': 'F2 Ab2 C3', 'G': 'G2 B2 D3', 'Db': 'Db3 F3 Ab3', 'Eb': 'Eb3 G3 Bb3', 'Bb': 'Bb2 D3 F3'}
    rt = {'Cm': 'C2', 'Ab': 'Ab1', 'Fm': 'F1', 'G': 'G1', 'Db': 'Db2', 'Eb': 'Eb2', 'Bb': 'Bb1'}
    pA = ['Cm', 'Ab', 'Fm', 'G', 'Cm', 'Ab', 'Db', 'G']; pB = ['Ab', 'Eb', 'Fm', 'Cm', 'Ab', 'Bb', 'Db', 'G']
    prog = ['Cm', 'Cm', 'Ab', 'G'] + pA + pB + pA
    mA = ("Eb4:6 G4:2 Ab4:4 G4:4  C4:12 R:4  Ab4:6 G4:2 F4:4 Eb4:4  D4:8 G3:8  "
          "Eb4:6 G4:2 Ab4:4 G4:4  C5:8 Bb4:4 Ab4:4  Db5:6 C5:2 Bb4:4 Ab4:4  G4:12 R:4")
    mB = ("C5:8 Eb5:4 C5:4  Bb4:8 G4:8  Ab4:4 C5:4 F5:4 Eb5:4  Eb5:8 D5:4 C5:4  "
          "C5:8 Ab4:8  D5:8 Bb4:8  F5:6 Eb5:2 Db5:4 C5:4  B4:8 D5:4 G5:4")
    lead = P(0.5, 1400, 0.12, 5, 0.03, 0.3, 0.65, 0.2)
    m = s.buf()
    for t_, bar in [(mA, 4), (mB, 12), (mA, 20)]: s.line(M(t_, 8), lead, bar, 1.0, out=m, gate=0.95)
    dbl = s.line(M(mA, 8, oct=1), P(0.125, 2200, 0.12, 5, 0.03, 0.3, 0.6, 0.2), 20, 1.0, gate=0.95)
    ost = []
    for p in prog: r = midi(rt[p]) + 12; ost += [(r, 4), (r, 4), (r - 4 if p in ('Cm',) else r + 7, 4), (r + 7 if p == 'Cm' else r, 4)]
    o = s.line(ost, PB(0.5, 700, 0.1), 0, 1.0, gate=1.0)
    toll = s.line([(midi(rt[p]) + 24, 16) for p in prog], BELL(0.6), 0, 1.0)
    pd = pad_chords(s, [q[p] for p in prog], PAD(800, 0.5, 0.8))
    g = {'l': 'x.......x...o.o.', 'k': 'x...............'}
    bars = [{'l': 'x...............'}] * 4 + [g] * 7 + [dict(g, t='........x.x.xxxx')] + [g] * 7 + [dict(g, s='............o.oo')] + [g] * 8
    dr = drums(s, bars, {'l': 0.35, 'k': 0.3, 't': 0.18, 's': 0.1})
    y = master_mono(s, [delay(m, 4 * s.step, fb=0.3, mix=0.3, damp=1500) * 0.5, dbl * 0.15, o * 0.3, toll * 0.05, pd * 0.1, dr * 0.8])
    return y, dict(key='C minor', bpm=80, meter='4/4', bars=28, form='intro A B A\' (motif Eb-G-Ab-G)')

# ================================================================== celebration
def celebration():
    """C major, 120 BPM, 48 bars (A B A C A B'). Joyful: house motif opens the tune, the new_era
    fanfare (E-G-C6-D6) returns in the C break with bells; bouncy bass, arps, warm drums. ~96 s, stereo."""
    s = Song2(120, 48, tail=6.0)
    q = {'C': 'C4 E4 G4', 'Am': 'A3 C4 E4', 'F': 'F3 A3 C4', 'G': 'G3 B3 D4', 'Dm': 'D4 F4 A4', 'Em': 'E3 G3 B3'}
    rt = {'C': 'C2', 'Am': 'A1', 'F': 'F1', 'G': 'G1', 'Dm': 'D2', 'Em': 'E2'}
    pA = ['C', 'Am', 'F', 'G', 'C', 'Am', 'Dm', 'C']; pB = ['F', 'G', 'Em', 'Am', 'F', 'G', 'C', 'G']; pC = ['C', 'C', 'Am', 'Am', 'F', 'C', 'G', 'G']
    prog = pA + pB + pA + pC + pA + pB
    mA = ("E5:3 G5:1 A5:2 G5:2 C6:4 G5:4  A5:3 G5:1 E5:2 C5:2 E5:8  F5:2 A5:2 C6:2 A5:2 F5:4 A5:4  G5:6 F5:2 E5:4 D5:4  "
          "E5:3 G5:1 A5:2 G5:2 C6:4 E6:4  D6:4 C6:4 A5:4 E5:4  F5:4 A5:4 G5:4 B5:4  C6:12 R:4")
    mB = ("A5:4 C6:4 A5:2 G5:2 F5:4  G5:4 B5:4 G5:2 F5:2 D5:4  E5:4 G5:4 B5:4 G5:4  A5:12 R:4  "
          "F5:2 G5:2 A5:2 C6:2 D6:4 C6:4  B5:2 A5:2 G5:2 B5:2 D6:8  E5:2 G5:2 C6:2 E6:2 D6:4 C6:4  D6:8 B5:4 G5:4")
    mC = ("E5:2 G5:2 C6:4 D6:8  R:16  E5:2 G5:2 C6:4 E6:8  R:16  F5:4 A5:4 C6:4 A5:4  G5:4 C6:4 E6:4 C6:4  D6:4 B5:4 G5:4 B5:4  D6:8 R:8")
    lead = P(0.25, 3400, 0.15, 5.5, 0.006, 0.15, 0.62, 0.1)
    m = s.buf()
    for t_, bar in [(mA, 0), (mB, 8), (mA, 16), (mC, 24), (mA, 32), (mB, 40)]: s.line(M(t_, 8), lead, bar, 1.0, out=m, gate=0.88)
    h = s.buf()
    for bar in (32,): s.line(M(mA, 8, oct=-1), P(0.125, 2500, 0.12, 5.5, 0.006, 0.15, 0.6, 0.1), bar, 1.0, out=h, gate=0.88)
    bells = s.buf()
    for b in range(24, 32, 2): s.line([(midi('C6'), 4), (midi('G5'), 4), (midi('E6'), 8)], BELL(0.3), b, 1.0, out=bells)
    ar = s.line(chords_to_arp([q[p] for p in prog], [0, 1, 2, 3, 2, 1], 16, 2), P(0.125, 3000, 0, 5, 0.003, 0.08, 0.3, 0.05), 0, 1.0, gate=0.7)
    bs = bass_line(s, [rt[p] for p in prog], [(12, 4), (19, 2), (24, 2), (12, 4), (19, 4)], BASS(1500, 0.01, 0.08))
    pd = pad_chords(s, [q[p] for p in prog], PAD(1000, 0.1, 0.3))
    g = {'k': 'x.......x.......', 's': '....x.......x...', 'h': '..o...o...o...o.', 'z': 'o.o.o.o.o.o.o.o.'}
    gf = dict(g, s='....x.......x.xo', t='..........x.x...')
    brk = {'k': 'x...............', 'z': 'o.o.o.o.o.o.o.o.', 'j': 'x...x...x...x...'}
    bars = ([g] * 7 + [gf]) * 3 + [brk] * 7 + [gf] + ([g] * 7 + [gf]) * 2
    dr = drums(s, bars, {'k': 0.4, 's': 0.13, 'h': 0.04, 'z': 0.04, 't': 0.2, 'j': 0.05})
    eL, eR = pingpong(m * 0.4 + ar * 0.15 + bells * 0.06, 3 * s.step, fb=0.35, mix=0.55, damp=2800, width=1.0)
    y = master_st(s, [(m * 0.4, 0), (h * 0.2, 0.2), (bells * 0.06, 0.25), (ar * 0.15, -0.35), (bs * 0.45, 0), (pd * 0.05, 0), (dr * 0.75, 0.05)], eL, eR)
    return y, dict(key='C major', bpm=120, meter='4/4', bars=48, form='A B A C(new_era fanfare break) A B\'')

# ================================================================== storm
def storm():
    """E minor, 100 BPM, 32 bars (A B A' bridge). Under a storm, safe inside: swirling 16th triangle
    arpeggios, a warm anxious pulse tune, deep bass swells, soft rain hiss and distant low rumbles
    (gentle, not noisy). ~77 s, stereo."""
    s = Song2(100, 32, tail=7.0)
    q = {'Em': 'E3 G3 B3', 'C': 'C3 E3 G3', 'Am': 'A2 C3 E3', 'B': 'B2 D#3 F#3', 'D': 'D3 F#3 A3', 'Bm': 'B2 D3 F#3', 'B7': 'B2 D#3 A3'}
    rt = {'Em': 'E1', 'C': 'C2', 'Am': 'A1', 'B': 'B1', 'D': 'D2', 'Bm': 'B1', 'B7': 'B1'}
    pA = ['Em', 'C', 'Am', 'B', 'Em', 'C', 'D', 'B']; pB = ['C', 'D', 'Bm', 'Em', 'C', 'D', 'B', 'B7']; pD = ['Em', 'Em', 'C', 'C', 'Am', 'Am', 'B', 'B']
    prog = pA + pB + pA + pD
    mA = ("B4:4 E5:4 F#5:4 G5:4  E5:8 G5:4 C6:4  B5:6 A5:2 G5:4 E5:4  F#5:12 R:4  "
          "B4:4 E5:4 G5:4 B5:4  C6:8 B5:4 G5:4  A5:6 G5:2 F#5:4 D5:4  D#5:12 R:4")
    mB = ("E5:6 G5:2 C6:4 B5:4  A5:6 F#5:2 D5:8  D5:4 F#5:4 B5:4 A5:4  G5:12 R:4  "
          "C6:6 B5:2 A5:4 G5:4  F#5:6 G5:2 A5:8  B5:4 A5:4 G5:4 F#5:4  F#5:12 R:4")
    lead = P(0.25, 2800, 0.16, 5.8, 0.01, 0.2, 0.62, 0.15)
    m = s.buf()
    for t_, bar in [(mA, 0), (mB, 8), (mA, 16)]: s.line(M(t_, 8), lead, bar, 1.0, out=m, gate=0.92)
    lowm = s.line(M("E3:8 G3:8  E3:8 C3:8  A2:8 C3:8  B2:16  E3:8 B3:8  G3:8 E3:8  C3:8 E3:8  F#3:8 D#3:8", 8), T(1500, 0.1, 5, 0.03, 0.2, 0.75, 0.2), 24, 1.0, gate=1.0)
    ar = s.line(chords_to_arp([q[p] for p in prog], [0, 1, 2, 3, 4, 3, 2, 1], 16, 1), T(2600, 0, 5, 0.003, 0.06, 0.4, 0.04, steps=True), 0, 1.0, gate=0.8)
    bs = s.line([(midi(rt[p]) + 12, 16) for p in prog], BASS(500, 0.3, 0.4), 0, 1.0, gate=1.0)
    pd = pad_chords(s, [q[p] for p in prog], PAD(900, 0.3, 0.6))
    M_ = s.L + s.tail; rain = bp(R().normal(0, 1, M_), 900, 5000) * (1 + 0.15 * lp(R().normal(0, 1, M_), 1) * 30)
    rain = np.clip(rain, -4, 4)
    rum = s.buf()
    for bar in (0, 9, 17, 24, 28):
        n = N(3.0); tt = np.arange(n) / SR
        place(rum, lp(R().normal(0, 1, n), 120) * np.minimum(tt / 0.6, 1) * np.exp(-np.maximum(tt - 0.6, 0) / 0.8), s.ts(bar * 16 + 4), 1.0)
    g = {'k': 'x.........x.....', 'z': 'o.o.o.o.o.o.o.o.'}; gB = {'k': 'x.........x.....', 's': '....o.......o...', 'z': 'o.o.o.o.o.o.o.o.'}
    bars = [g] * 8 + [gB] * 8 + [g] * 8 + [{'l': 'x.......o.......'}] * 7 + [{'l': 'x...o...o.o.oooo'}]
    dr = drums(s, bars, {'k': 0.35, 's': 0.1, 'z': 0.03, 'l': 0.3})
    eL, eR = pingpong(m * 0.4 + ar * 0.12, 3 * s.step, fb=0.4, mix=0.55, damp=2200, width=1.0)
    y = master_st(s, [(m * 0.4, 0), (lowm * 0.25, 0), (ar * 0.12, -0.35), (bs * 0.45, 0), (pd * 0.14, 0.1), (rain * 0.006, -0.35), (rain[::-1].copy() * 0.006, 0.35), (rum * 0.35, 0), (dr * 0.7, 0)], eL, eR)
    return y, dict(key='E minor', bpm=100, meter='4/4', bars=32, form='A B A\' bridge')

# ================================================================== winter
def winter():
    """Winter house_day: same tune, same chords, same 86 BPM and 32 bars as house_day (C major).
    Wintry arrangement: tune on a soft triangle (A) and a music box (A'), bell doubling in B',
    sparse sleigh-jingles on beats 2 and 4 in the B sections only, whole-note bass, soft pad, no drums.
    ~89 s, stereo."""
    s = Song2(86, 32, tail=8.0)
    A_ch = ['C4 E4 G4 B4', 'A3 C4 E4 G4', 'F3 A3 C4 E4', 'G3 B3 D4 G4', 'C4 E4 G4 B4', 'E3 G3 B3 D4', 'F3 A3 C4 E4', 'G3 B3 D4 F4']
    A2_ch = A_ch[:6] + ['G3 B3 D4 G4', 'C4 E4 G4 C5']
    B_ch = ['F3 A3 C4 E4', 'G3 B3 D4 G4', 'E3 G3 B3 D4', 'A3 C4 E4 G4', 'D3 F3 A3 C4', 'G3 B3 D4 F4', 'C4 E4 G4 B4', 'G3 B3 D4 G4']
    chords = A_ch + B_ch + A2_ch + B_ch[:7] + ['G3 B3 D4 F4']
    roots = ['C2', 'A1', 'F1', 'G1', 'C2', 'E2', 'F1', 'G1', 'F1', 'G1', 'E2', 'A1', 'D2', 'G1', 'C2', 'G1',
             'C2', 'A1', 'F1', 'G1', 'C2', 'E2', 'G1', 'C2', 'F1', 'G1', 'E2', 'A1', 'D2', 'G1', 'C2', 'G1']
    melA = ("E5:6 G5:2 A5:4 G5:4  E5:8 D5:4 C5:4  A4:6 C5:2 D5:4 E5:4  D5:12 R:4 "
            "E5:6 G5:2 C6:4 A5:4  G5:8 E5:4 D5:4  C5:4 D5:4 E5:4 A5:4  G5:12 R:4")
    melA2 = melA.rsplit('C5:4 D5:4 E5:4 A5:4  G5:12 R:4', 1)[0] + "D5:4 E5:4 G5:4 D5:4  C5:16"
    melB = ("A5:4 G5:4 A5:4 C6:4  D6:8 B5:4 G5:4  G5:6 E5:2 D5:4 E5:4  C5:8 E5:4 A5:4 "
            "F5:6 E5:2 D5:4 A4:4  B4:4 D5:4 G5:8  E5:6 D5:2 C5:4 G4:4  A4:4 B4:4 D5:8")
    melB2 = melB.rsplit('A4:4 B4:4 D5:8', 1)[0] + "D5:6 E5:2 D5:4 B4:4"
    soft = T(3000, 0.14, 4.8, 0.03, 0.35, 0.6, 0.35, steps=False)
    m = s.buf()
    s.line(M(melA, 8), soft, 0, 1.0, out=m); s.line(M(melB, 8), soft, 8, 1.0, out=m)
    s.line(M(melA2, 8), BOX(0.55, 4200), 16, 1.6, out=m); s.line(M(melB2, 8), soft, 24, 1.0, out=m)
    bl = s.line(M(melB2, 8, oct=1), BELL(0.35), 24, 1.0)
    ar = s.line(chords_to_arp(chords, [0, 2, 1, 3, 2, 1, 3, 2], 16, 2), BOX(0.3, 3500), 0, 1.0)
    pd = pad_chords(s, chords, PAD(1200, 0.4, 0.8))
    bs = s.line([(midi(r) + 12, 16) for r in roots], BASS(800, 0.1, 0.5), 0, 1.0, gate=1.0)
    jb = {'j': '....x.......x...'}
    dr = drums(s, [None] * 8 + [jb] * 8 + [None] * 8 + [jb] * 8, {'j': 0.06})
    sparkle = s.buf()
    for bar in range(0, 32, 4):
        f = fq(R().choice(['E6', 'G6', 'C7'])); n = N(0.4); tt = np.arange(n) / SR
        place(sparkle, np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.12), s.ts(bar * 16 + int(R().choice([6, 10, 14]))), 1.0)
    eL, eR = pingpong(m * 0.45 + ar * 0.18 + bl * 0.06 + sparkle * 0.03, 3 * s.step * 2, fb=0.42, mix=0.45, damp=2400, width=0.85)
    y = master_st(s, [(m * 0.45, 0), (bl * 0.06, 0.2), (ar * 0.18, -0.3), (pd * 0.09, 0), (bs * 0.45, 0), (dr, 0.2), (sparkle * 0.03, 0.3)], eL, eR)
    return y, dict(key='C major', bpm=86, meter='4/4', bars=32, form='A B A\' B\' (house_day)')

PIECES = [('nursery', nursery, 8001), ('pond', pond, 8002), ('cellar', cellar, 8003), ('workshop', workshop, 8004),
          ('tension', tension, 8005), ('fight', fight, 8006), ('grief', grief, 8007), ('vengeance', vengeance, 8008),
          ('celebration', celebration, 8009), ('storm', storm, 8010), ('winter', winter, 8011)]
if __name__ == '__main__':
    only = set(sys.argv[1:]); meta = {}
    for name, fn, sd in PIECES:
        if only and name not in only: continue
        seed(sd); y, info = fn(); write(f'{OUT}/{name}', y); meta[name] = info
        print(f'{name:12s} {len(y)/SR:6.2f}s {"st" if y.ndim > 1 else "mo"} {lufs(y):6.2f} LUFS {true_peak_db(y):6.2f} dBTP  {info["key"]} {info["bpm"]}', flush=True)
