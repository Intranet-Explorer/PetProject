"""Batch 1: time-of-day music + transition jingles for 'the house'.
house_night (C major, 3/4, 72 BPM, stereo), outdoors_day (F major, 100 BPM, stereo),
outdoors_night (A minor / C major pentatonic, 54 BPM, stereo), jingles dawn & dusk (C major, mono).
Same procedural toolkit as synth.py: pulse/triangle/noise, envelopes, filters, echo.
Stereo = dry voices in the centre + ping-pong echo taps split L/R (no phase tricks -> mono-safe)."""
from synth import *
from music import vib, drums
OUTM = '/workspace/house-audio/music'; OUTJ = '/workspace/house-audio/jingles'
os.makedirs(OUTM, exist_ok=True); os.makedirs(OUTJ, exist_ok=True)

class Song2:
    def __init__(s, bpm, bars, spb=16, tail=10.0):
        s.bpm, s.bars, s.spb = bpm, bars, spb
        s.step = 60 / bpm / 4; s.L = N(bars * spb * s.step); s.tail = N(tail)
    def buf(s): return np.zeros(s.L + s.tail)
    def ts(s, step): return int(round(step * s.step * SR))
    def line(s, notes, instr, start_bar=0, gain=1.0, out=None, gate=0.95):
        out = s.buf() if out is None else out; pos = start_bar * s.spb
        for m, st in notes:
            if m is not None:
                d = st * s.step
                place(out, instr(hz(m), d, d * gate, pos * s.step), s.ts(pos), gain)
            pos += st
        return out

def mel(txt, bars, spb):
    notes = parse(txt); tot = sum(st for _, st in notes)
    assert tot == bars * spb, (tot, bars * spb, txt[:40]); return notes

def chords_to_arp(chords, pattern, spb, steps_per_note):
    out = []
    for ch in chords:
        tones = [midi(n) for n in ch.split()]
        for i in range(spb // steps_per_note):
            idx = pattern[i % len(pattern)]
            out.append((tones[idx % len(tones)] + 12 * (idx // len(tones)), steps_per_note))
    return out

def pingpong(x, dt, fb=0.4, mix=0.4, damp=3000, width=0.8, nrep=14):
    """Echo taps alternating L/R. Returns (eL, eR); add the same dry signal to both channels."""
    eL, eR = np.zeros_like(x), np.zeros_like(x); rep = x.copy(); D = N(dt)
    for k in range(1, nrep + 1):
        rep = lp(rep, damp, 1) * fb
        if np.max(np.abs(rep)) < 1e-5 or D * k >= len(x): break
        s = np.zeros_like(x); s[D * k:] = rep[:len(x) - D * k]
        a = (1 + width) / 2 if k % 2 else (1 - width) / 2
        eL += s * mix * a; eR += s * mix * (1 - a)
    return eL, eR

def master_st(song, parts, eL, eR, target=-20.0):
    """parts: list of (signal, pan in [-1,1]). Linear amplitude pan (gL=1-p, gR=1+p, |p|<=0.35)
    keeps the mono sum identical to the unpanned mix -> fully mono-compatible."""
    chans = []
    for side, e in ((-1, eL), (1, eR)):
        dry = sum(x * (1 + side * p) for x, p in parts)
        c = hp(lp(dry + e, 12000), 25)
        y = c[:song.L].copy(); t = c[song.L:]; y[:len(t)] += t       # fold tail into start: seamless loop
        chans.append(y)
    st = np.stack(chans, axis=1)
    st, _ = loop_finalize(st, near=0)
    return level(st, target)

# ----------------------------------------------------------------------------------------------
def house_night():
    """C major lullaby in 3/4, 72 BPM, 32 bars (A B A' B'). Melody re-uses house_day's opening
    motif (E-G-A-G | E-D-C) stretched into waltz time; triangle music-box arpeggios, soft bass."""
    s = Song2(72, 32, spb=12)
    A = ['C4 E4 G4 B4', 'A3 C4 E4 G4', 'F3 A3 C4 E4', 'G3 B3 D4 G4', 'C4 E4 G4 B4', 'A3 C4 E4 G4', 'D4 F4 A4 C5', 'G3 B3 D4 F4']
    B = ['F3 A3 C4 E4', 'E3 G3 B3 D4', 'D4 F4 A4 C5', 'C4 E4 G4 B4', 'F3 A3 C4 E4', 'E3 G3 B3 D4', 'D4 F4 A4 C5', 'G3 B3 D4 F4']
    B2 = B[:7] + ['C4 E4 G4 C5']
    chords = A + B + A + B2
    roots = ['C2', 'A1', 'F1', 'G1', 'C2', 'A1', 'D2', 'G1', 'F1', 'E2', 'D2', 'C2', 'F1', 'E2', 'D2', 'G1'] * 2
    roots[-1] = 'C2'
    melA = ("E5:6 G5:2 A5:2 G5:2  E5:8 D5:2 C5:2  A4:6 C5:2 D5:2 E5:2  D5:12 "
            "E5:6 G5:2 C6:2 A5:2  G5:8 E5:4  F5:4 E5:4 D5:4  D5:8 R:4")
    melB = ("A5:6 G5:2 F5:2 E5:2  G5:8 E5:4  F5:6 E5:2 D5:4  E5:12 "
            "A4:4 C5:4 F5:4  G5:6 E5:2 D5:4  F5:4 E5:4 D5:4  D5:8 R:4")
    melA2 = ("C5:6 E5:2 G5:2 E5:2  C5:8 B4:2 A4:2  A4:6 C5:2 D5:2 E5:2  D5:12 "
             "E5:6 G5:2 C6:2 A5:2  G5:8 E5:4  F5:4 E5:4 D5:4  B4:8 R:4")
    melB2 = melB.rsplit('D5:8 R:4', 1)[0] + "C5:12"
    def lead(f, d, g, t0):
        n = N(d + 0.4); tt = np.arange(n) / SR
        duty = 0.125 + 0.07 * (1 - np.exp(-tt / 0.6))
        x = pulse(vib(f, n, 0.15, 4.8, 0.35, 0.4), n / SR, duty)
        return lp(x, 2200) * adsr(n, 0.04, 0.35, 0.6, 0.35, N(g))
    def box(f, d, g, t0):      # music box: stepped triangle, plucked decay
        n = N(d + 0.6); return lp(tri(f, n / SR), 4000) * expenv(n, 0.45, 0.004)
    def bass(f, d, g, t0):
        n = N(d + 0.3); return lp(tri(f, n / SR), 1200) * adsr(n, 0.03, 0.6, 0.7, 0.3, N(g))
    m = s.buf()
    for t_, bar in [(melA, 0), (melB, 8), (melA2, 16), (melB2, 24)]:
        s.line(mel(t_, 8, 12), lead, bar, 1.0, out=m)
    # A' melody on the music box an octave up, very soft (night 'echo' of the tune)
    s.line(mel(melA2, 8, 12), lambda f, d, g, t0: box(f * 2, d, g, t0), 16, 0.18, out=m)
    ar = s.line(chords_to_arp(chords, [0, 2, 1, 3, 2, 1], 12, 2), box, 0, 1.0)
    bl = [(midi(r) + 12, 12) for r in roots]
    bs = s.line(bl, bass, 0, 1.0, gate=1.0)
    dry = [(m * 0.55, 0.0), (ar * 0.30, -0.3), (bs * 0.55, 0.0)]
    eL, eR = pingpong(m * 0.55 + ar * 0.3, 3 * s.step * 2, fb=0.42, mix=0.5, damp=2200)   # dotted-8th
    return master_st(s, dry, eL, eR)

def outdoors_day():
    """F major, 100 BPM, 32 bars (A B A' B). Airy: wide leaps in the tune, open-voiced 12.5% pulse
    arpeggios bouncing in ping-pong echo, long triangle bass, light shaker/kick only."""
    s = Song2(100, 32)
    A = ['F3 C4 G4 A4', 'G3 D4 F4 Bb4', 'Bb3 F4 A4 D5', 'C4 G4 Bb4 E5', 'F3 C4 G4 A4', 'D4 A4 C5 F5', 'Bb3 F4 A4 D5', 'C4 F4 G4 C5']
    A2 = A[:7] + ['F3 C4 G4 A4']
    B = ['Bb3 F4 C5 D5', 'C4 G4 Bb4 E5', 'A3 E4 G4 C5', 'D4 A4 C5 F5', 'G3 D4 F4 Bb4', 'C4 G4 Bb4 E5', 'F3 C4 G4 A4', 'C4 G4 Bb4 D5']
    chords = A + B + A2 + B
    roots = ['F2', 'G2', 'Bb1', 'C2', 'F2', 'D2', 'Bb1', 'C2', 'Bb1', 'C2', 'A1', 'D2', 'G1', 'C2', 'F2', 'C2']
    roots = roots[:8] + roots[8:] + roots[:7] + ['F2'] + roots[8:]
    melA = ("C5:4 F5:4 G5:4 A5:4  Bb5:6 A5:2 G5:8  F5:4 D5:4 F5:4 A5:4  G5:12 R:4 "
            "C6:6 A5:2 F5:4 G5:4  A5:8 F5:4 D5:4  D5:4 F5:4 A5:4 G5:4  F5:4 E5:4 G5:8")
    melA2 = melA.rsplit('F5:4 E5:4 G5:8', 1)[0] + "F5:12 R:4"
    melB = ("D6:6 C6:2 Bb5:4 F5:4  G5:6 A5:2 Bb5:4 C6:4  A5:8 E5:4 G5:4  F5:12 R:4 "
            "Bb5:6 A5:2 G5:4 D5:4  E5:4 G5:4 C6:8  A5:6 G5:2 F5:4 C5:4  D5:4 E5:4 G5:8")
    def lead(f, d, g, t0):
        n = N(d + 0.2); x = pulse(vib(f, n, 0.18, 5.5, 0.22, 0.25), n / SR, 0.25)
        return lp(x, 4200) * adsr(n, 0.012, 0.18, 0.62, 0.15, N(g))
    def low(f, d, g, t0):
        n = N(d + 0.2); return tri(vib(f, n, 0.12, 5.5, 0.22), n / SR) * adsr(n, 0.015, 0.2, 0.7, 0.15, N(g))
    def arp(f, d, g, t0):
        n = N(d + 0.05); return lp(pulse(f, n / SR, 0.125), 3500) * adsr(n, 0.003, 0.09, 0.25, 0.04, N(g * 0.6))
    def bass(f, d, g, t0):
        n = N(d + 0.08); return lp(tri(f, n / SR), 2000) * adsr(n, 0.01, 0.3, 0.75, 0.08, N(g))
    m = s.buf(); lo = s.buf()
    for t_, bar in [(melA, 0), (melB, 8), (melA2, 16), (melB, 24)]:
        s.line(mel(t_, 8, 16), lead, bar, 1.0, out=m)
    for bar in (8, 24):   # B sections: triangle doubling an octave below for a fuller, open sound
        s.line([(None if n is None else n - 12, st) for n, st in mel(melB, 8, 16)], low, bar, 1.0, out=lo)
    ar = s.line(chords_to_arp(chords, [0, 1, 2, 3, 4, 3, 2, 1], 16, 2), arp, 0, 1.0, gate=0.8)
    bl = []
    for r in roots:
        mm = midi(r) + 12; bl += [(mm, 8), (mm + 7, 6), (mm + 12, 2)]
    bs = s.line(bl, bass, 0, 1.0, gate=1.0)
    g1 = {'k': 'x.......x.......', 's': '................', 'h': '..o...o...o...o.'}
    g2 = {'k': 'x.......x.....o.', 's': '....o.......o...', 'h': 'o.o.o.o.o.o.o.o.'}
    bars = [{'h': '..o...o...o...o.'}] * 4 + [g1] * 4 + [g2] * 8 + [g1] * 8 + [g2] * 8
    dr = drums(s, bars, {'k': 0.35, 's': 0.07, 'h': 0.06})
    dry = [(m * 0.5, 0.0), (lo * 0.22, 0.25), (ar * 0.22, -0.3), (bs * 0.55, 0.0), (dr * 0.7, 0.1)]
    eL, eR = pingpong(m * 0.5 + ar * 0.3, 3 * s.step, fb=0.4, mix=0.45, damp=3000, width=0.9)
    return master_st(s, dry, eL, eR)

def outdoors_night():
    """A few soft notes over space: A minor / C major pentatonic, 54 BPM, 16 bars of 2-bar chords
    (Am7 Fmaj7 Cmaj7 G6 | Am7 Fmaj7 Dm7 G6). Sparse triangle 'star' melody with long ping-pong
    echo, slow-swelling triangle chord pad, deep soft bass, occasional faint high twinkles."""
    s = Song2(54, 16)
    ch = ['A3 C4 E4 G4', 'F3 A3 C4 E4', 'C4 E4 G4 B4', 'G3 B3 D4 E4', 'A3 C4 E4 G4', 'F3 A3 C4 E4', 'D4 F4 A4 C5', 'G3 B3 D4 E4']
    roots = ['A1', 'F1', 'C2', 'G1', 'A1', 'F1', 'D2', 'G1']
    melo = ("R:4 E5:8 R:4 G5:4 A5:12  R:8 C6:8 A5:4 G5:12  E5:16 R:8 D5:4 E5:4  R:4 D5:12 R:16 "
            "R:8 A5:8 R:4 C6:4 E6:8  R:4 D6:4 C6:8 A5:16  R:8 F5:8 E5:4 D5:4 C5:8  D5:16 R:16")
    def star(f, d, g, t0):
        n = N(d + 1.2); return lp(tri(f, n / SR), 3500) * expenv(n, 0.9, 0.012)
    def pad(f, d, g, t0):
        n = N(d + 2.0); tt = np.arange(n) / SR
        x = tri(f * 2 ** (0.05 * np.sin(2 * np.pi * 0.3 * tt) / 12), n / SR, steps=False)
        return lp(x, 1200) * adsr(n, 1.4, 0.5, 0.8, 1.8, N(g))
    def bass(f, d, g, t0):
        n = N(d + 1.5); return lp(tri(f, n / SR), 600) * adsr(n, 0.25, 1.0, 0.6, 1.5, N(g))
    def twinkle(f, d, g, t0):
        n = N(0.25); return lp(pulse(f, 0.25, 0.125), 5000) * expenv(n, 0.06, 0.003)
    m = s.line(mel(melo, 16, 16), star, 0, 1.0)
    pd = s.buf()
    for i, c in enumerate(ch):
        for nm in c.split():
            s.line([(midi(nm), 32)], pad, 2 * i, 1.0, out=pd, gate=0.92)
    bs = s.line([(midi(r) + 12, 32) for r in roots], bass, 0, 1.0, gate=0.95)
    tw = s.buf(); pent = [midi(x) for x in ['E6', 'G6', 'A6', 'C7', 'D6']]
    for bar in range(1, 16, 2):           # one faint twinkle per 2 bars at a seeded off-beat position
        pos = bar * 16 + int(rng.choice([3, 7, 10, 13]))
        place(tw, twinkle(hz(pent[rng.integers(len(pent))]), 0.2, 0.2, 0), s.ts(pos), 1.0)
    dry = [(m * 0.55, 0.0), (pd * 0.12, 0.0), (bs * 0.5, 0.0), (tw * 0.08, 0.35)]
    eL, eR = pingpong(m * 0.55 + tw * 0.08, 3 * s.step * 2, fb=0.5, mix=0.55, damp=2000, width=0.9)
    return master_st(s, dry, eL, eR)

# ---------------------------------------- jingles ---------------------------------------------
def nt(inst, f, d, a=0.005, dk=0.2, sus=0.7, rel=0.2, gate=0.9, **kw):
    n = N(d + rel); x = inst(f, n / SR, **kw) if inst is not pulse else inst(f, n / SR, kw.get('duty', 0.25))
    return x * adsr(n, a, dk, sus, rel, N(d * gate))

def play(buf, seq, fn, gain=1.0):
    for t, name, d in seq:
        place(buf, fn(fq(name), d), float(t), gain)

def timeline(pairs, t0=0.0):
    out, t = [], t0
    for name, d in pairs:
        if name != 'R': out.append((t, name, d))
        t += d
    return out, t

def dawn():
    """Night -> day: slow Am7 music-box arpeggio rising (house_night colour), quickening through
    Fmaj7 and G with brightening pulse, then house_day's opening motif (E-G-A-G) landing on a
    C major chord at 86 BPM. ~8.7 s."""
    dur = 11.0; b = np.zeros(N(dur)); sx = 60 / 86 / 4      # house_day 16th
    box = lambda f, d: lp(tri(f, d + 0.8), 4000) * expenv(N(d + 0.8), 0.5, 0.004)
    a1, t = timeline([(n, 0.34) for n in ['A3', 'C4', 'E4', 'G4', 'A4', 'C5', 'E5', 'G5']])
    for i, (tt, nm, d) in enumerate(a1):
        place(b, box(fq(nm), d), tt, 0.25 + 0.03 * i)
    p = lambda f, d: lp(pulse(f, d + 0.15, 0.125), 3000 + 0) * adsr(N(d + 0.15), 0.003, 0.08, 0.35, 0.1, N(d * 0.8))
    a2, t2 = timeline([(n, sx) for n in ['F4', 'A4', 'C5', 'E5', 'F5', 'E5', 'C5', 'A4']], t)
    a3, t3 = timeline([(n, sx) for n in ['G4', 'B4', 'D5', 'G5', 'B5', 'D6']], t2)
    play(b, a2 + a3, p, 0.32)
    lead = lambda f, d: lp(pulse(vib(f, N(d + 0.3), 0.18, 5.2, 0.25), d + 0.3, 0.25), 3200) * adsr(N(d + 0.3), 0.012, 0.2, 0.65, 0.3, N(d * 0.92))
    mo, t4 = timeline([('E5', 3 * sx), ('G5', sx), ('A5', 2 * sx), ('G5', 2 * sx)], t3)
    play(b, mo, lead, 0.5)
    fin = 1.6
    place(b, lead(fq('C6'), fin), t4, 0.45)
    chord = lambda f, d: lp(pulse(f, d + 0.8, 0.5), 1600) * adsr(N(d + 0.8), 0.02, 0.4, 0.5, 0.8, N(d))
    for nm in ['C4', 'E4', 'G4']:
        place(b, chord(fq(nm), fin), t3, 0.12)
    bass = lambda f, d: lp(tri(f, d + 0.5), 1500) * adsr(N(d + 0.5), 0.03, 0.4, 0.75, 0.5, N(d))
    for tt, nm, d in [(0, 'A2', t), (t, 'F2', t2 - t), (t2, 'G2', t3 - t2), (t3, 'C2', t4 + fin - t3)]:
        place(b, bass(fq(nm), d), tt, 0.5)
    place(b, hp(noise(1.2, 30000), 7000) * expenv(N(1.2), 0.3, 0.05), t4, 0.03)
    return delay(b, 3 * sx, fb=0.35, mix=0.35, damp=2500)

def dusk():
    """Day -> night: house_day's motif at day tempo over C, then a ritardando falling through Am7
    and Fmaj7 as pulse gives way to triangle, ending on house_night's waltz-time music box
    (E-G-A-G, D) settling on a low, soft C. ~8.6 s."""
    dur = 11.0; b = np.zeros(N(dur)); sx = 60 / 86 / 4; e8 = 60 / 72 / 2   # house_night 8th
    lead = lambda f, d: lp(pulse(vib(f, N(d + 0.3), 0.15, 5.0, 0.25), d + 0.3, 0.25), 3000) * adsr(N(d + 0.3), 0.012, 0.2, 0.65, 0.3, N(d * 0.92))
    box = lambda f, d: lp(tri(f, d + 0.9), 3800) * expenv(N(d + 0.9), 0.55, 0.004)
    m1, t1 = timeline([('E5', 3 * sx), ('G5', sx), ('A5', 2 * sx), ('G5', 2 * sx)])
    m2, t2 = timeline([('E5', 0.5), ('D5', 0.6), ('C5', 0.85)], t1)
    play(b, m1 + m2, lead, 0.5)
    p = lambda f, d: lp(pulse(f, d + 0.15, 0.125), 3000) * adsr(N(d + 0.15), 0.003, 0.08, 0.35, 0.1, N(d * 0.8))
    ar1, _ = timeline([(n, sx) for n in ['C4', 'E4', 'G4', 'C5', 'E5', 'C5', 'G4', 'E4']])
    play(b, ar1, p, 0.25)
    ar2, ta = timeline([(n, 0.27) for n in ['A4', 'G4', 'E4', 'C4']], t1)
    ar3, tb = timeline([(n, 0.37) for n in ['A4', 'F4', 'E4', 'C4']], ta)
    play(b, ar2 + ar3, box, 0.3)
    m3, t3 = timeline([('E5', 3 * e8 / 2 * 1.0), ('G5', e8 / 2), ('A5', e8 / 2), ('G5', e8), ('D5', 2 * e8)], tb)
    play(b, m3, box, 0.42)
    place(b, box(fq('C5'), 1.6), t3, 0.42)
    place(b, box(fq('C4'), 1.6), t3, 0.25)
    bass = lambda f, d: lp(tri(f, d + 0.6), 1200) * adsr(N(d + 0.6), 0.03, 0.5, 0.7, 0.6, N(d))
    g_at = t3 - 2 * e8
    for tt, nm, d in [(0, 'C2', t1), (t1, 'A1', ta - t1), (ta, 'F1', tb - ta), (tb, 'C2', g_at - tb), (g_at, 'G1', 2 * e8), (t3, 'C2', 1.4)]:
        place(b, bass(fq(nm) * 2, d), tt, 0.5)
    pad = lambda f, d: lp(tri(f, d + 1.0, steps=False), 1200) * adsr(N(d + 1.0), 0.5, 0.5, 0.8, 1.0, N(d))
    for nm in ['C4', 'E4', 'G4']:
        place(b, pad(fq(nm), 1.4), t3, 0.08)
    return delay(b, 3 * e8 / 2, fb=0.35, mix=0.35, damp=2200)

if __name__ == '__main__':
    for name, fn in [('house_night', house_night), ('outdoors_day', outdoors_day), ('outdoors_night', outdoors_night)]:
        y = fn(); write(f'{OUTM}/{name}', y)
        print(f'{name:16s} {len(y)/SR:6.2f}s {lufs(y):6.2f} LUFS {true_peak_db(y):6.2f} dBTP')
    for name, fn, T in [('dawn', dawn, 9.3), ('dusk', dusk, 9.3)]:
        y = hp(fn(), 25)[:N(T)].copy()
        f = N(1.3); y[-f:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, f))   # let the final chord/echo die away
        y = level(trim_sfx(y, tail_keep=0.05, fade_out=0.05), -16.0)
        write(f'{OUTJ}/{name}', y)
        print(f'{name:16s} {len(y)/SR:6.2f}s {lufs(y):6.2f} LUFS {true_peak_db(y):6.2f} dBTP')
