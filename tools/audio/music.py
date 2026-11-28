from synth import *
OUT = '/workspace/house-audio/music'; os.makedirs(OUT, exist_ok=True)

class Song:
    def __init__(self, bpm, bars):
        self.step = 60 / bpm / 4; self.bars = bars
        self.L = N(bars * 16 * self.step); self.tail = N(6.0)
    def buf(self): return np.zeros(self.L + self.tail)
    def ts(self, step): return int(round(step * self.step * SR))
    def line(self, notes, instr, start_bar=0, gain=1.0, out=None, gate=0.92):
        out = self.buf() if out is None else out; pos = start_bar * 16
        for m, st in notes:
            if m is not None:
                d = st * self.step
                x = instr(hz(m), d, d * gate, self.ts(pos) / SR)
                place(out, x, self.ts(pos), gain)
            pos += st
        return out, pos
    def loopfold(self, x):
        y = x[:self.L].copy(); t = x[self.L:]; y[:len(t)] += t; return y

def vib(f, n, depth, rate=5.5, delay_s=0.2, ramp=0.25):
    t = np.arange(n) / SR
    return f * 2 ** (depth * np.sin(2 * np.pi * rate * t) * np.clip((t - delay_s) / ramp, 0, 1) / 12)

def chord_notes(names): return [midi(x) for x in names.split()]

def arp_line(chords, pattern, steps_per_note=1):
    """chords: list of chord-tone lists (one per bar); pattern: indices into tones"""
    out = []
    for ch in chords:
        for i in range(16 // steps_per_note):
            idx = pattern[i % len(pattern)]
            out.append((ch[idx % len(ch)] + 12 * (idx // len(ch)), steps_per_note))
    return out

def drums(song, pattern_bars, gains):
    """pattern: dict name->16-char string per bar ('x' hit, 'o' soft, '.' rest)"""
    out = song.buf()
    def kick():
        d = 0.16; return tri(expsweep(140, 42, d), d) * expenv(N(d), 0.06, 0.001)
    def snare():
        d = 0.18; n = N(d)
        return (0.7 * bp(noise(d, 14000), 800, 7000) * expenv(n, 0.05, 0.001) +
                0.4 * tri(expsweep(220, 160, d), d) * expenv(n, 0.03, 0.001))
    def hat():
        d = 0.05; return hp(noise(d, 44100), 6500) * expenv(N(d), 0.012, 0.0005)
    inst = {'k': kick, 's': snare, 'h': hat}
    for b, pat in enumerate(pattern_bars):
        if pat is None: continue
        for name, row in pat.items():
            for i, ch in enumerate(row):
                if ch in 'xo':
                    place(out, inst[name](), song.ts(b * 16 + i), gains[name] * (1 if ch == 'x' else 0.45))
    return out

TARGET = -20.0
def master(song, tracks):
    mix = sum(tracks)
    mix = hp(lp(mix, 13000), 25)
    y = song.loopfold(mix)                 # fold the release/echo tail into the start -> seamless loop
    y, rot = loop_finalize(y, near=0)       # start on the upward zero crossing nearest the downbeat
    return level(y, TARGET)

# ======================= MYSTERIOUS (D dorian / D harmonic minor) =======================
def mysterious():
    s = Song(92, 32)
    A_ch = ['D4 F4 A4', 'G3 B3 D4', 'D4 F4 A4', 'C4 E4 G4', 'D4 F4 A4', 'G3 B3 D4', 'F3 A3 C4', 'A3 C#4 E4']
    A2_ch = A_ch[:7] + ['D4 F4 A4']
    B_ch = ['Bb3 D4 F4', 'G3 Bb3 D4', 'E3 G3 Bb3', 'A3 C#4 E4', 'Bb3 D4 F4', 'G3 Bb3 D4', 'A3 C#4 E4', 'A3 C#4 G4']
    chords = A_ch + A2_ch + B_ch + A2_ch
    roots = ['D2', 'G2', 'D2', 'C2', 'D2', 'G2', 'F2', 'A2'] + ['D2', 'G2', 'D2', 'C2', 'D2', 'G2', 'F2', 'D2'] + \
            ['Bb1', 'G2', 'E2', 'A2', 'Bb1', 'G2', 'A2', 'A2'] + ['D2', 'G2', 'D2', 'C2', 'D2', 'G2', 'F2', 'D2']
    melA = ("A4:6 D5:2 E5:4 F5:4  G5:4 F5:2 E5:2 D5:4 B4:4  A4:8 R:4 F5:2 E5:2  E5:6 D5:2 C5:4 E5:4 "
            "D5:6 A5:2 G5:4 F5:4  E5:4 F5:2 G5:2 B4:8  C5:4 A4:4 F5:4 E5:4  E5:12 C#5:4")
    melA2 = melA.rsplit('E5:12', 1)[0] + "D5:16"
    melB = ("F5:4 D5:4 Bb4:4 D5:4  G5:8 Bb5:4 A5:4  G5:6 E5:2 Bb4:8  A5:4 G5:2 F5:2 E5:4 C#5:4 "
            "D5:4 F5:4 Bb5:6 A5:2  G5:4 F5:2 E5:2 D5:8  E5:4 F5:4 G5:4 C#5:4  E5:8 R:8")
    # first A: melody up an octave lower on a soft triangle-ish voice for an "intro" feel
    def lead(f, d, g, t0, duty=0.25):
        n = N(d + 0.15); x = pulse(vib(f, n, 0.25, 5.0, 0.22), n / SR, duty)
        return lp(x, 4500) * adsr(n, 0.01, 0.15, 0.6, 0.12, N(g))
    def soft(f, d, g, t0):
        n = N(d + 0.15); x = tri(vib(f, n, 0.2, 5.0, 0.2), n / SR)
        return x * adsr(n, 0.02, 0.2, 0.7, 0.12, N(g))
    def arp(f, d, g, t0):
        n = N(d + 0.03); return pulse(f, n / SR, 0.125) * adsr(n, 0.002, 0.07, 0.25, 0.02, N(g * 0.7))
    def bass(f, d, g, t0):
        # legato (batch 0): release overlaps the next note so bass note-offs don't open gaps
        n = N(d + 0.07); return tri(f, n / SR) * adsr(n, 0.01, 0.1, 0.85, 0.07, N(g))

    m1, _ = s.line(parse(melA), soft, 0, 1.0)
    m2, _ = s.line(parse(melA2), lead, 8, 1.0)
    m3, _ = s.line(parse(melB), lead, 16, 1.0)
    m4, _ = s.line(parse(melA2), lead, 24, 1.0)
    # harmony voice in B section: sustained thirds below, very quiet
    melody = m1 * 0.55 + (m2 + m3 + m4) * 0.42
    melody = delay(melody, 6 * s.step, fb=0.4, mix=0.45, damp=2500)       # dotted-8th echo
    ch = [chord_notes(c) for c in chords]
    pat = [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 4, 3, 2, 1, 2, 3]
    ar, _ = s.line(arp_line(ch, pat), arp, 0, 1.0, gate=0.8)
    ar = delay(ar, 3 * s.step, fb=0.45, mix=0.5, damp=2200)               # dotted-16th smear
    bl = []
    for b, r in enumerate(roots):
        m = midi(r)
        if b < 8: bl += [(m, 8), (m + 7, 8)]
        else: bl += [(m, 6), (m, 2), (m + 7, 4), (m + 12, 4)]
    bs, _ = s.line(bl, bass, 0, 1.0, gate=1.0)
    groove = {'k': 'x.........x.....', 's': '........o.......', 'h': '..o...o...o...o.'}
    groovB = {'k': 'x.....x...x.....', 's': '........x.......', 'h': '..o.o.o...o.o.o.'}
    fill = {'k': 'x.........x.....', 's': '........o...o.oo', 'h': '..o...o...o.....'}
    bars = [None] * 7 + [{'h': '........o.o.o.o.'}] + [groove] * 7 + [fill] + [groovB] * 7 + [fill] + [groove] * 7 + [fill]
    dr = drums(s, bars, {'k': 0.55, 's': 0.25, 'h': 0.10})
    return master(s, [melody * 0.9, ar * 0.32, bs * 0.55, dr * 0.8])

# ======================= RELAXING (C major pentatonic, 86 bpm) =======================
def relaxing():
    s = Song(86, 32)
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
    song_t0 = [0.0]
    def lead(f, d, g, t0):
        n = N(d + 0.25); tt = np.arange(n) / SR
        # warm low-duty pulse: duty breathes between 12.5% and 25% within the note + slow song-level LFO
        lfo = 0.5 + 0.5 * np.sin(2 * np.pi * (t0 + tt) / (s.L / SR / 4))
        duty = 0.125 + 0.125 * (0.4 * lfo + 0.6 * (1 - np.exp(-tt / 0.35)))
        x = pulse(vib(f, n, 0.18, 5.2, 0.25, 0.3), n / SR, duty)
        return lp(x, 3200) * adsr(n, 0.02, 0.25, 0.65, 0.2, N(g))
    def pad(f, d, g, t0):
        n = N(d + 0.08); x = pulse(f, n / SR, 0.5)
        return lp(x, 1800) * adsr(n, 0.01, 0.15, 0.35, 0.08, N(g))
    def bass(f, d, g, t0):
        # legato: gate = full note, 70 ms release overlaps the next note's 15 ms attack (fixes the dips)
        n = N(d + 0.07); return lp(tri(f, n / SR), 2500) * adsr(n, 0.015, 0.2, 0.8, 0.07, N(g))

    m = s.buf()
    for mel, bar in [(melA, 0), (melB, 8), (melA2, 16), (melB2, 24)]:
        s.line(parse(mel), lead, bar, 1.0, out=m)
    m = delay(m, 4 * s.step, fb=0.3, mix=0.35, damp=2200)
    ch = [chord_notes(c) for c in chords]
    pad_pat = [0, 2, 1, 3, 2, 1, 3, 2]
    pd, _ = s.line(arp_line(ch, pad_pat, 2), pad, 0, 1.0, gate=0.95)
    pd = delay(pd, 6 * s.step, fb=0.3, mix=0.3, damp=1800)
    bl = []
    for r in roots:
        mm = midi(r); bl += [(mm + 12, 6), (mm + 19, 2), (mm + 24, 4), (mm + 19, 4)]
    bs, _ = s.line(bl, bass, 0, 1.0, gate=1.0)
    g1 = {'k': 'x.........o.....', 's': '........o.......', 'h': 'o.o.o.o.o.o.o.o.'}
    g2 = {'k': 'x.....o...o.....', 's': '........o.......', 'h': 'o.o.o.oo o.o.o.o'.replace(' ', '.')}
    end = {'k': 'x.........o.....', 's': '........o...o.o.', 'h': 'o.o.o.o.o.o.....'}
    bars = [{'h': 'o.o.o.o.o.o.o.o.'}] * 4 + [g1] * 3 + [end] + [g2] * 7 + [end] + [g1] * 7 + [end] + [g2] * 7 + [end]
    dr = drums(s, bars, {'k': 0.4, 's': 0.12, 'h': 0.06})
    return master(s, [m * 0.75, pd * 0.16, bs * 0.6, dr * 0.7])

if __name__ == '__main__':
    for name, fn in [('attic', mysterious), ('house_day', relaxing)]:
        y = fn(); write(f'{OUT}/{name}', y)
        print(name, round(len(y) / SR, 2), 's', round(lufs(y), 2), 'LUFS', round(true_peak_db(y), 2), 'dBTP')
