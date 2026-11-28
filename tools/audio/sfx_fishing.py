"""Fishing SFX for 'the house' (batch 0). Procedural: pulse/square/triangle/noise only.
Each file: render -> 25 Hz high-pass -> trim lead/trail silence + short fade -> level to -16 LUFS
(integrated, BS.1770-4) with a lookahead true-peak limiter at -1 dBTP if needed."""
from synth import *
OUT = '/workspace/house-audio/sfx'; os.makedirs(OUT, exist_ok=True)
TARGET = -16.0

def cast():
    dur = 1.4; buf = np.zeros(N(dur))
    wd = 0.45; n = N(wd); t = np.arange(n) / SR
    fc = np.interp(t, [0, 0.18, wd], [400, 5000, 900])
    w = lp_sweep(noise(wd, 30000), fc) * np.sin(np.pi * np.clip(t / wd, 0, 1)) ** 1.5
    w[:N(0.004)] += 0  # whoosh swells from the first sample
    place(buf, w, 0.0, 0.9)
    sw = pulse(expsweep(1600, 250, 0.3), 0.3, 0.125) * expenv(N(0.3), 0.09, 0.01)
    place(buf, fade(sw), 0.0, 0.18)
    ld = 1.05; n = N(ld); t = np.arange(n) / SR
    f = expsweep(950, 380, ld); trem_rate = expsweep(45, 11, ld)
    trem = 0.55 + 0.45 * (np.sin(2 * np.pi * np.cumsum(trem_rate) / SR) > 0)
    env = np.minimum(t / 0.04, 1) * np.exp(-t / 0.55)
    whir = pulse(f, ld, 0.25) * trem * env + 0.25 * hp(noise(ld), 3000) * trem * env
    place(buf, fade(lp(whir, 6000), 0.005, 0.08), 0.28, 0.45)
    return buf

def reel():
    # ratchet clicks only (old 220 Hz triangle hum removed: it was a 1.6 s steady tone)
    dur = 1.6; buf = np.zeros(N(dur)); t = 0.0; k = 0
    while t < dur - 0.05:
        n = N(0.03)
        click = bp(noise(0.03), 1800, 7000) * expenv(n, 0.007, 0.0008)
        blip = pulse(2300 if k % 2 else 1750, 0.03, 0.5) * expenv(n, 0.006, 0.0008)
        body = tri(rng.uniform(380, 460), 0.03, steps=False) * expenv(n, 0.011, 0.001)
        lvl = (0.55 + 0.45 * min(1, t / 0.15)) * min(1, (dur - t) / 0.2)
        place(buf, lp(0.5 * click + 0.3 * blip + 0.35 * body, 7000) * lvl, t)
        t += 1 / 15 + rng.uniform(-0.004, 0.004); k += 1
    # soft spool rustle (noise, no pitch) under the clicks
    rs = lp(noise(dur, 44100), 1500) * 0.09 * (0.6 + 0.4 * np.sin(2 * np.pi * 15 * np.arange(N(dur)) / SR))
    return buf + fade(rs, 0.01, 0.2)

def plop():
    dur = 0.9; buf = np.zeros(N(dur))
    b = tri(expsweep(260, 1100, 0.08), 0.08) * expenv(N(0.08), 0.05, 0.002)
    place(buf, fade(b, 0.001, 0.01), 0.0, 0.9)
    sd = 0.5; n = N(sd); t = np.arange(n) / SR
    sp = lp_sweep(noise(sd, 9000), np.interp(t, [0, sd], [6000, 700])) * expenv(n, 0.11, 0.005)
    place(buf, sp, 0.03, 0.7)
    for tt, g in [(0.24, 0.35), (0.37, 0.25), (0.52, 0.15)]:
        d = tri(expsweep(900, 1800, 0.04), 0.04) * expenv(N(0.04), 0.02, 0.001)
        place(buf, fade(d, 0.001, 0.005), tt, g)
    return buf

def nibble():
    dur = 0.75; buf = np.zeros(N(dur))
    for tt in (0.0, 0.17):
        tug = tri(expsweep(700, 300, 0.05), 0.05) * expenv(N(0.05), 0.03, 0.001)
        place(buf, fade(tug, 0.001, 0.005), tt, 0.6)
        place(buf, lp(noise(0.08, 12000), 3000) * expenv(N(0.08), 0.02), tt + 0.01, 0.2)
    a = pulse(fq('B5'), 0.07, 0.25) * adsr(N(0.07), 0.002, 0.02, 0.8, 0.01, N(0.06))
    place(buf, lp(a, 5000), 0.38, 0.45)
    # held "!" note: was 0.45 s of 50% square; now 0.16 s hold + 0.07 s release, 25% duty, low-passed
    hd = 0.25; n = N(hd); t = np.arange(n) / SR
    f = fq('E6') * 2 ** (0.25 * np.sin(2 * np.pi * 12 * t) / 12)
    e = pulse(f, hd, 0.25) * adsr(n, 0.002, 0.05, 0.6, 0.07, N(0.13))
    place(buf, lp(e, 5000), 0.46, 0.45)
    return buf

def note(name, dur_s, duty=0.5, vib=0.0, inst=pulse, gate_frac=0.85, rel=0.03, lpf=6000):
    n = N(dur_s); t = np.arange(n) / SR
    f = fq(name) * 2 ** (vib * np.sin(2 * np.pi * 6 * t) * np.clip((t - 0.08) / 0.15, 0, 1) / 12)
    x = inst(f, dur_s, duty) if inst is pulse else inst(f, dur_s)
    return lp(x, lpf) * adsr(n, 0.003, 0.06, 0.75, rel, N(dur_s * gate_frac))

def caught():
    dur = 1.6; buf = np.zeros(N(dur)); step = 0.075
    seq = [('G4', 1), ('C5', 1), ('E5', 1), ('G5', 2), ('E5', 1), ('G5', 1)]
    t = 0.0
    for nm, st in seq:
        place(buf, note(nm, st * step + 0.02), t, 0.5); t += st * step
    # final chord: was a 1.0 s held C6 (+ held bass); now a re-articulated broken-chord flourish
    t_end = t
    flour = ['C6', 'G5', 'E5', 'G5', 'C6', 'E6', 'C6', 'G5', 'E5', 'C5']
    for i, nm in enumerate(flour):
        g = 0.55 * (0.82 ** i)
        place(buf, note(nm, 0.085, 0.5, gate_frac=0.75, rel=0.02), t, g)
        place(buf, note(nm, 0.085, 0.25, gate_frac=0.75, rel=0.02), t + 0.02, g * 0.3)
        t += 0.07
    for nm, tt, d in [('C3', 0, 0.22), ('G2', 0.3, 0.2), ('C3', t_end, 0.22), ('G2', t_end + 0.24, 0.2), ('C3', t_end + 0.48, 0.25)]:
        place(buf, note(nm, d, inst=tri, gate_frac=0.75, rel=0.05), tt, 0.6)
    cr = hp(noise(0.6, 25000), 4000) * expenv(N(0.6), 0.18)
    place(buf, cr, t_end, 0.12)
    return buf

def snap():
    dur = 1.85; buf = np.zeros(N(dur))
    place(buf, hp(noise(0.06), 1500) * expenv(N(0.06), 0.012, 0.0005), 0.0, 0.8)
    sw = pulse(expsweep(3200, 180, 0.09), 0.09, 0.125) * expenv(N(0.09), 0.04, 0.0005)
    place(buf, fade(sw, 0.0005, 0.01), 0.0, 0.35)
    notes = [('G4', 'C3', 0.24), ('F#4', 'B2', 0.24), ('F4', 'Bb2', 0.24), ('E4', 'A2', 0.85)]
    t = 0.26
    for i, (ld, bs, d) in enumerate(notes):
        n = N(d); tt = np.arange(n) / SR; last = i == 3
        bend = -0.6 * np.exp(-tt / 0.03)
        if last:   # short hold, then a continuous sad droop (no held tone > 0.3 s)
            bend += 0.3 * np.sin(2 * np.pi * 5 * tt) * np.clip((tt - 0.06) / 0.1, 0, 1)
            bend += -3.0 * np.clip((tt - 0.09) / 0.6, 0, 1)
        x = pulse(fq(ld) * 2 ** (bend / 12), d, np.linspace(0.5, 0.25, n))
        x = lp(x, 3500) * adsr(n, 0.01, 0.1, 0.7, 0.3 if last else 0.03, N(d * (0.62 if last else 0.9)))
        place(buf, x, t, 0.5)
        bb = bend if last else 0
        b = tri(fq(bs) * 2 ** (np.asarray(bb) / 12), d) * adsr(n, 0.005, 0.05, 0.9, 0.3 if last else 0.03, N(d * (0.62 if last else 0.9)))
        place(buf, b, t, 0.45)
        t += d
    return buf

def sparkle():
    """Rare catch: bigger & brighter than the caught jingle - 3-voice rising run over ~3.5 octaves,
    a bright chord bloom, then a 2-voice pentatonic shimmer spanning C5-G7 with echo."""
    dur = 1.95; buf = np.zeros(N(dur))
    run = ['C4', 'D4', 'E4', 'G4', 'A4', 'C5', 'D5', 'E5', 'G5', 'A5', 'C6', 'D6', 'E6', 'G6']
    st = 0.03
    for i, nm in enumerate(run):
        m = midi(nm)
        place(buf, pulse(hz(m), 0.06, 0.25) * adsr(N(0.06), 0.002, 0.02, 0.6, 0.015, N(0.045)), i * st, 0.30)
        place(buf, pulse(hz(m + 12), 0.05, 0.125) * adsr(N(0.05), 0.002, 0.02, 0.5, 0.015, N(0.035)), i * st + 0.012, 0.16)
        place(buf, tri(hz(m - 24), 0.06) * adsr(N(0.06), 0.002, 0.03, 0.7, 0.015, N(0.045)), i * st, 0.45)
    tb = len(run) * st
    # chord bloom: C major add9 across 3 octaves, struck together, short decay
    for nm, g in [('C3', 0.5), ('G3', 0.35), ('C5', 0.22), ('E5', 0.2), ('G5', 0.2), ('D6', 0.15), ('E6', 0.15), ('G6', 0.13), ('C7', 0.1)]:
        inst = tri if midi(nm) < 60 else (lambda f, d: pulse(f, d, 0.125 if midi(nm) > 80 else 0.25))
        x = inst(fq(nm), 0.32) * expenv(N(0.32), 0.09, 0.002)
        place(buf, fade(x, 0.001, 0.02), tb, g)
    place(buf, hp(noise(0.5, 36000), 6000) * expenv(N(0.5), 0.12, 0.002), tb, 0.12)
    # shimmer: two random pentatonic voices per tick, never repeating a pitch within 4 ticks
    pent = [midi(n) for n in ['C5', 'D5', 'E5', 'G5', 'A5', 'C6', 'D6', 'E6', 'G6', 'A6', 'C7', 'D7', 'E7', 'G7']]
    t = tb + 0.08; recent = []
    while t < 1.55:
        for v in range(2):
            choices = [m for m in pent if m not in recent]
            m = choices[rng.integers(len(choices))]; recent = (recent + [m])[-8:]
            x = pulse(hz(m), 0.045, 0.125 if m > 84 else 0.25) * expenv(N(0.045), 0.013, 0.001)
            place(buf, fade(x, 0.001, 0.005), t + v * 0.012, 0.22 * (1 - 0.7 * (t - tb) / 1.2))
        t += 0.034
    place(buf, hp(noise(1.2, 30000), 7000) * expenv(N(1.2), 0.35, 0.05), tb, 0.05)
    return lp(delay(buf, 0.14, fb=0.3, mix=0.4, damp=8000), 11000)

FILES = [('fish_cast', cast), ('fish_reel_in', reel), ('fish_bobber_plop', plop),
         ('fish_nibble_alert', nibble), ('fish_caught_jingle', caught),
         ('fish_line_snap_got_away', snap), ('fish_rare_catch_sparkle', sparkle)]
if __name__ == '__main__':
    for name, fn in FILES:
        x = level(trim_sfx(hp(fn(), 25)), TARGET)
        write(f'{OUT}/{name}', x)
        print(f'{name:28s} {len(x)/SR:5.2f}s  {lufs(x):6.2f} LUFS  {true_peak_db(x):6.2f} dBTP')
