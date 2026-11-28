"""Batch 7: books, creatures, life (sfx), event jingles, UI. Procedural, retro-cozy.
Jingles share house_day's key (C major) and opening motif E5-G5-A5-G5 at 86 BPM (16th = 0.174 s).
sfx/ui: render -> 40 Hz HP -> trim + 20 ms fade -> target LUFS (-16; ui/click & ui/hover -24, see credits), <= -1 dBTP.
jingles: render -> 30 Hz HP -> trim (50 ms tail, 50 ms fade) -> -16 LUFS."""
import sys
from hands_sfx import g, rustle, thump, nz, seed, R, j, blip, note, bell, ping, click, sparkle, mix
from machines_sfx import metal, chirp, wood, hump
from music_batch1 import timeline
from music import vib
from synth import *
ROOT = '/workspace/house-audio'
SX = 60 / 86 / 4                                      # house_day 16th note
MOTIF = [('E5', 3 * SX), ('G5', SX), ('A5', 2 * SX), ('G5', 2 * SX)]
TARGETS = {'ui/click': -24.0, 'ui/hover': -24.0}

def sine_glide(f0, f1, d, env_p=1.5):
    n = N(d); return np.sin(2 * np.pi * np.cumsum(expsweep(f0, f1, d)) / SR) * hump(n, env_p)
def strokes(k, dmin, dmax, lo, hi, glo, ghi, grate, body=0.3):
    b = []; t = 0.0
    for i in range(k):
        d = j(dmin, dmax); n = N(d); grit = np.zeros(n); kk = 0.0
        while kk < d: place(grit, g(0.006, glo, ghi, 0.0015), N(kk), j(0.3, 1.0)); kk += j(0.5, 1.5) / grate
        b.append((t, (bp(nz(n), lo, hi) * body + grit * 0.6) * hump(n, 0.8), j(0.6, 1.0))); t += d + j(0.04, 0.12)
    return b, t
# instruments (as house_day / dawn)
def lead(f, d, dep=0.15):
    n = N(d + 0.25); return lp(pulse(vib(f, n, dep, 5.2, 0.12, 0.15), n / SR, 0.25), 3200) * adsr(n, 0.01, 0.15, 0.6, 0.22, N(d * 0.92))
def box(f, d, tau=0.35):
    n = N(d + 0.6); return lp(tri(f, n / SR), 4000) * expenv(n, tau, 0.003)
def pls(f, d):
    n = N(d + 0.12); return lp(pulse(f, n / SR, 0.125), 3000) * adsr(n, 0.003, 0.08, 0.35, 0.1, N(d * 0.8))
def chordv(f, d):
    n = N(d + 0.5); return lp(pulse(f, n / SR, 0.5), 1600) * adsr(n, 0.02, 0.3, 0.5, 0.5, N(d))
def bass(f, d):
    n = N(d + 0.3); return lp(tri(f, n / SR), 1400) * adsr(n, 0.02, 0.3, 0.75, 0.3, N(d))
def seq(items, inst, t0=0.0, gain=1.0):
    ev, t = timeline(items, t0); return [(tt, inst(fq(nm), d), gain) for tt, nm, d in ev], t

# ------------------------------------------------------------------ books / radio / paint
def page_turn():
    d = 0.38; n = N(d); fl = np.zeros(n); k = 0.0
    while k < d - 0.01: place(fl, g(0.01, 1800, 6000, 0.0025), N(k), j(0.2, 0.8) * np.sin(np.pi * k / d)); k += j(0.008, 0.025)
    swish = lp_sweep(bp(nz(n), 600, 5000), np.linspace(1500, 4000, n)) * hump(n, 1.3) * 0.25
    return mix(0.55, [(0, click(1500, 4000, 0.002), 0.3), (0.02, fl + swish, 1.0), (0.38, thump(150, 240, 0.012), 0.25), (0.38, g(0.04, 800, 3000, 0.008), 0.25)])
def book_close():
    n = N(0.13); wh = bp(nz(n), 400, 2500) * hump(n, 1.5) * 0.25
    return mix(0.5, [(0, wh, 1.0), (0.12, thump(85, 150, 0.04), 1.0), (0.12, g(0.06, 250, 1500, 0.015), 0.6), (0.12, click(1000, 3500, 0.003), 0.3),
                     (0.13, g(0.05, 1500, 5000, 0.006), 0.15)])
def quill_write():
    b, t = strokes(int(R().integers(4, 6)), 0.12, 0.3, 2000, 5000, 2200, 5500, 180, 0.15)
    return mix(t + 0.05, [(0, click(2500, 5500, 0.0012), 0.3)] + [(tt + 0.03, x, a) for tt, x, a in b])
def static(n):
    st = bp(nz(n), 300, 4500) * np.clip(1 + 0.5 * lp(nz(n), 30) * 5, 0.2, None) * 0.35
    cr = np.zeros(n); k = 0.0
    while k < n / SR - 0.01: place(cr, g(0.006, 1000, 5000, 0.001), N(k), j(0.2, 1.0)); k += R().exponential(1 / 40)
    return st + cr * 0.25
def radio_static():
    d = 1.6; n = N(d); t = np.arange(n) / SR
    s = static(n); whistle = lp(np.sin(2 * np.pi * np.cumsum(expsweep(1400, 600, d) * 2 ** (40 * np.sin(2 * np.pi * 3 * t) / 1200)) / SR), 3000) * 0.05
    voice = bp(nz(n), 350, 1400) * np.clip(np.sin(2 * np.pi * 4.3 * t + 3 * lp(nz(n), 4)), 0, None) * 0.15   # garbled far-off voice
    return (s + whistle + voice) * np.minimum(t / 0.03, 1) * np.clip((d - t) / 0.3, 0, 1)
def radio_on():
    d = 0.9; n = N(d); t = np.arange(n) / SR
    s = static(n) * np.clip(1 - (t - 0.35) / 0.3, 0.12, 1) * np.minimum(t / 0.08, 1)
    tune = np.sin(2 * np.pi * np.cumsum(expsweep(1800, 500, 0.4)) / SR) * hump(N(0.4), 1) * 0.08
    tune_items = [(0.55 + i * 0.13, bp(pls(fq(nm), 0.1), 300, 3000), 0.35) for i, nm in enumerate(['C5', 'E5', 'G5'])]
    return mix(1.3, [(0, click(800, 3000, 0.003), 0.6), (0, thump(140, 220, 0.01), 0.4), (0.02, s, 1.0), (0.05, tune, 1.0)] + tune_items)
def radio_off():
    d = 0.35; n = N(d); t = np.arange(n) / SR
    s = lp_sweep(static(n), np.geomspace(4000, 300, n)) * np.exp(-t / 0.12)
    return mix(0.5, [(0, click(800, 3000, 0.003), 0.6), (0, thump(140, 220, 0.01), 0.4), (0.0, s, 1.0), (0.01, blip(500, 180, 0.15, 0.25), 0.25)])
def brush():
    b, t = strokes(3, 0.22, 0.32, 700, 3500, 1500, 4500, 90, 0.35)
    return mix(t + 0.05, b)

# ------------------------------------------------------------------ creatures
def bird(v):
    e = []; t = 0.0
    if v == 1:     # 'tee-yoo, tee-yoo'
        for rep in range(2):
            for fa, fb, d in [(2300, 2900, 0.13), (2800, 2000, 0.17)]:
                e.append((t, sine_glide(fa * j(0.97, 1.03), fb, d), 0.8 - 0.2 * rep)); t += d + 0.03
            t += 0.15
    elif v == 2:   # quick rising trill
        for i in range(9):
            f = 2000 + 120 * i; e.append((t, sine_glide(f, f * 1.25, 0.04), 0.5 + 0.04 * i)); t += 0.055
        e.append((t + 0.04, sine_glide(3000, 2300, 0.18), 0.8)); t += 0.24
    else:          # three falling chirps + tweedle
        for i in range(3):
            f = j(3000, 3300); e.append((t, sine_glide(f, f * 0.7, 0.07), 0.8)); t += 0.13
        for i in range(4):
            e.append((t, sine_glide(2400 if i % 2 else 2800, 2600 if i % 2 else 3100, 0.05), 0.6)); t += 0.06
    return lp(mix(t + 0.1, e), 5500)
def owl():
    f0 = j(380, 420); e = []; t = 0.0
    for d, gap, drop in [(0.26, 0.2, 140), (0.13, 0.06, 120), (0.38, 0.0, 240)]:
        n = N(d); tt = np.arange(n) / SR; fr = f0 * 2 ** ((60 - drop * tt / d) / 1200)
        x = (np.sin(2 * np.pi * np.cumsum(fr) / SR) + 0.15 * np.sin(4 * np.pi * np.cumsum(fr) / SR)) * hump(n, 1.5) + 0.08 * lp(nz(n), 1200) * hump(n)
        e.append((t, x, 1.0)); t += d + gap
    return lp(delay(mix(t + 0.4, e), 0.13, fb=0.25, mix=0.3, damp=1200), 1500)
def frog():
    e = []; t = 0.0
    for d, f in [(0.13, 330), (0.2, 300)]:
        n = N(d); f *= j(0.97, 1.03)
        am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 32 * np.arange(n) / SR))
        x = lp(pulse(expsweep(f * 1.1, f * 0.88, d), d, 0.25) * am, 2000) * hump(n, 0.7)
        e.append((t, x, 1.0)); t += d + 0.07
    return mix(t + 0.05, e)
def rabbit():
    e = []
    for i, tt in enumerate([0.0, 0.17, 0.34]):
        e += [(tt, thump(60, 110, 0.05), 1.0 - 0.15 * i), (tt, g(0.05, 300, 1500, 0.01), 0.35)]
        for _ in range(5): e.append((tt + j(0, 0.05), g(0.01, 500, 2500, 0.003), j(0.1, 0.25)))
    return mix(0.6, e)
def squirrel():
    e = []; t = 0.0
    for i in range(int(R().integers(8, 12))):
        f = j(2400, 3200); a = j(0.6, 1.0); e += [(t, sine_glide(f, f * j(0.7, 0.85), j(0.025, 0.04), 1.0), 0.6 * a), (t, g(0.03, 2000, 5000, 0.004), 0.15 * a)]
        t += j(0.045, 0.07)
        if i == 4: t += 0.12
    e.append((t + 0.02, rustle(0.15, 800, 3500), 0.5))
    return lp(mix(t + 0.2, e), 5000)
def hedgehog():
    e = []; t = 0.0
    for i in range(int(R().integers(6, 9))):
        d = j(0.04, 0.09); n = N(d)
        e.append((t, bp(nz(n), j(400, 600), j(1200, 1800)) * hump(n, 0.6), j(0.4, 0.8))); t += d + j(0.03, 0.09)
    e.append((t * 0.6, sine_glide(650, 520, 0.08), 0.2))           # tiny grunt
    e.append((0.0, rustle(t, 600, 2500, 40), 0.3))
    return mix(t + 0.05, e)

# ------------------------------------------------------------------ eggs / life
def egg_laid():
    return mix(0.75, [(0, sine_glide(520, 200, 0.12, 1.0), 0.4), (0.05, thump(110, 180, 0.03), 0.8), (0.05, rustle(0.3, 700, 3500), 0.5),
                      (0.38, note('C6', 0.06), 0.25), (0.45, note('E6', 0.08), 0.25)])
def egg_wobble():
    e = []; t = 0.0
    for i in range(4):
        f = 950 if i % 2 == 0 else 1120
        e += [(t, ping(f * j(0.98, 1.02), 0.012), 0.6), (t, thump(170, 260, 0.01), 0.5), (t, rustle(0.1, 800, 3000), 0.25)]; t += 0.14 - 0.012 * i
    return mix(t + 0.15, e)
def egg_hatch():
    e = []; t = 0.0
    for i in range(3):                                   # cracks
        for _ in range(int(R().integers(3, 6))): e.append((t + j(0, 0.03), g(0.012, 1500, 6000, j(0.001, 0.003)), j(0.4, 1.0)))
        e.append((t, ping(j(1800, 2400), 0.006), 0.25)); t += j(0.17, 0.24)
    e.append((t, sine_glide(700, 250, 0.06, 1.0), 0.5))  # pop open
    for _ in range(5): e.append((t + j(0.02, 0.2), metal(j(1600, 2400), 0.012, 0.05), 0.06))   # shell bits
    for k, (fa, fb) in enumerate([(1800, 2300), (1900, 2500)]): e.append((t + 0.2 + k * 0.16, sine_glide(fa, fb, 0.09), 0.35))  # peep peep
    return lp(mix(t + 0.55, e), 6000)
def grow_up():
    items, t = seq([(nm, 0.06) for nm in ['C5', 'E5', 'G5', 'C6', 'E6']], lambda f, d: pls(f, d), 0.0, 0.45)
    n = N(0.3); sw = lp_sweep(nz(n), np.geomspace(800, 5000, n)) * hump(n) * 0.1
    items += [(0, sw, 1.0), (t, bell(fq('G5'), 0.22), 0.35), (t, bell(fq('C6'), 0.24), 0.4), (t + 0.04, sparkle(0.5, 7), 0.8)]
    return mix(t + 1.0, items)
def grow_old():
    items, t = seq([('E5', 0.32), ('D5', 0.32), ('C5', 0.36), ('A4', 0.5)], lambda f, d: box(f, d, 0.28), 0.0, 0.5)
    items += [(0.0, box(fq('C4'), 1.0, 0.28), 0.18), (0.68, box(fq('A3'), 1.0, 0.28), 0.18)]
    y = delay(mix(1.95, items), 0.24, fb=0.3, mix=0.3, damp=2000); f = N(0.35); y[-f:] *= np.cos(np.linspace(0, np.pi / 2, f)) ** 2
    return y
def death_knell():
    f = fq('G3'); n = N(1.95); t = np.arange(n) / SR; y = np.zeros(n)
    for r, a, tau in [(0.5, 0.5, 0.3), (1.0, 1.0, 0.38), (1.19, 0.5, 0.32), (1.5, 0.35, 0.26), (2.0, 0.4, 0.2), (2.52, 0.2, 0.12), (3.0, 0.12, 0.09)]:
        y += a * np.sin(2 * np.pi * f * r * t + R().uniform(0, 6.28)) * np.exp(-t / tau)
    y = lp(y * np.minimum(t / 0.004, 1), 3000) + 0.2 * lp(nz(n), 900) * np.exp(-t / 0.01)
    return y * np.clip((1.95 - t) / 0.4, 0, 1)
def stone_placed():
    gr = np.zeros(N(0.3))
    for _ in range(14): place(gr, g(0.012, 500, 2500, 0.003), N(j(0, 0.2)), j(0.2, 0.6))
    return mix(0.7, [(0, thump(55, 100, 0.06), 1.0), (0, g(0.08, 200, 900, 0.02), 0.5), (0.01, gr, 0.5), (0.02, metal(900, 0.025, 0.12), 0.08),
                     (0.3, thump(70, 120, 0.025), 0.25), (0.3, rustle(0.15, 500, 2500), 0.25)])

# ------------------------------------------------------------------ jingles (C major, house_day motif)
def fin_chord(t, names, d, gain=0.12):
    return [(t, chordv(fq(nm), d), gain) for nm in names]
def j_first():
    items, t = seq(MOTIF, lead, 0.0, 0.5)
    items += [(t, lead(fq('C6'), 0.7), 0.45), (t, bell(fq('C6'), 0.24), 0.3), (t, bell(fq('G6'), 0.2), 0.15), (t + 0.05, sparkle(0.5, 6), 0.7)]
    items += [(0, bass(fq('C3'), t), 0.4), (t, bass(fq('C3'), 0.7), 0.4)] + fin_chord(t, ['E4', 'G4', 'C5'], 0.7)
    return delay(mix(t + 1.2, items), 3 * SX, fb=0.3, mix=0.3, damp=2500)
def j_invention():
    items, t = seq([(nm, SX / 2) for nm in ['C5', 'E5', 'G5', 'C6']], pls, 0.0, 0.35)
    m, t = seq([('E6', SX), ('G6', SX), ('A6', SX), ('G6', SX)], lambda f, d: lead(f / 2, d), t, 0.5)   # motif, quick (E5-G5-A5-G5)
    items += m + [(t, lead(fq('C6'), 0.6), 0.45), (t, bell(fq('C6'), 0.24), 0.35), (t, bell(fq('E6'), 0.2), 0.2), (t + 0.04, sparkle(0.6, 9), 0.9)]
    items += [(0, bass(fq('G2'), t), 0.4), (t, bass(fq('C3'), 0.6), 0.45)] + fin_chord(t, ['E4', 'G4', 'C5'], 0.6)
    return delay(mix(t + 1.1, items), 3 * SX, fb=0.3, mix=0.3, damp=2500)
def j_project_done():
    m1, t = seq(MOTIF, lead, 0.0, 0.45)
    m2, _ = seq([('C5', 3 * SX), ('E5', SX), ('F5', 2 * SX), ('E5', 2 * SX)], lead, 0.0, 0.3)       # harmony a third below
    m3, t2 = seq([('D5', 2 * SX), ('E5', 2 * SX)], lead, t, 0.45)
    m4, _ = seq([('B4', 2 * SX), ('C5', 2 * SX)], lead, t, 0.3)
    items = m1 + m2 + m3 + m4 + [(t2, lead(fq('C6'), 0.8), 0.45), (t2, lead(fq('G5'), 0.8), 0.25), (t2, bell(fq('C6'), 0.24), 0.3), (t2 + 0.05, sparkle(0.5, 6), 0.6)]
    for tt, nm, d in [(0, 'C3', 4 * SX), (4 * SX, 'F2', 4 * SX), (t, 'G2', 4 * SX), (t2, 'C3', 0.8)]: items.append((tt, bass(fq(nm), d), 0.45))
    items += fin_chord(t2, ['C4', 'E4', 'G4'], 0.8)
    return delay(mix(t2 + 1.3, items), 3 * SX, fb=0.3, mix=0.3, damp=2500)
def j_new_era():
    """Biggest jingle: snare-roll swell + rising C arpeggio, house_day motif harmonised in thirds climbing to C6-D6,
    over C-Am-G, landing on a full C major chord with bells, sparkle and a soft boom. ~3.9 s."""
    items = []
    n = N(0.55); roll = np.zeros(n)
    for k in np.arange(0, 0.55, 0.03): place(roll, g(0.03, 1500, 6000, 0.008), N(k), 0.2 + 1.4 * k)
    items.append((0, roll, 0.35))
    ar, m0 = seq([(nm, SX / 2) for nm in ['C4', 'E4', 'G4', 'C5', 'E5', 'G5']], pls, 0.0, 0.3)
    items += ar
    m, t = seq(MOTIF + [('C6', 2 * SX), ('D6', 2 * SX)], lead, m0, 0.5)
    h, _ = seq([('C5', 3 * SX), ('E5', SX), ('F5', 2 * SX), ('E5', 2 * SX), ('G5', 2 * SX), ('B5', 2 * SX)], lead, m0, 0.28)
    items += m + h
    fin = 1.0
    items += [(t, lead(fq('E6'), fin), 0.45), (t, lead(fq('C6'), fin), 0.35), (t, lead(fq('G5'), fin), 0.25)]
    items += [(t, bell(fq('C6'), 0.24), 0.35), (t, bell(fq('G6'), 0.2), 0.2), (t + 0.1, bell(fq('E6'), 0.22), 0.2), (t + 0.05, sparkle(0.8, 11), 1.0)]
    for tt, nm, d in [(0, 'C3', m0 + 4 * SX), (m0 + 4 * SX, 'A2', 4 * SX), (m0 + 8 * SX, 'G2', 4 * SX), (t, 'C2', fin), (t, 'C3', fin)]: items.append((tt, bass(fq(nm), d), 0.45))
    items += fin_chord(m0, ['C4', 'E4', 'G4'], 4 * SX, 0.08) + fin_chord(m0 + 4 * SX, ['C4', 'E4', 'A4'], 4 * SX, 0.08) + fin_chord(m0 + 8 * SX, ['B3', 'D4', 'G4'], 4 * SX, 0.08)
    items += fin_chord(t, ['C4', 'E4', 'G4', 'C5'], fin, 0.12)
    items += [(t, thump(70, 130, 0.06), 0.6), (t, lp(hp(nz(N(1.0)), 4000), 9000) * expenv(N(1.0), 0.25, 0.003), 0.06)]
    y = delay(mix(3.95, items), 3 * SX, fb=0.3, mix=0.3, damp=2500)
    f = N(0.5); y[-f:] *= np.cos(np.linspace(0, np.pi / 2, f)) ** 2       # let the final chord fade inside 4 s
    return y
def j_something_new():
    items, t = seq([('G5', SX), ('A5', SX), ('C6', SX), ('R', SX), ('D6', 2 * SX)], lambda f, d: box(f, d, 0.25), 0.0, 0.5)
    items += [(0, sparkle(0.4, 5), 0.6), (5 * SX, bell(fq('D6'), 0.2), 0.25), (0, bass(fq('C3'), 3 * SX), 0.3), (4 * SX, bass(fq('G2'), 2 * SX), 0.3)]
    return delay(mix(t + 0.7, items), 3 * SX, fb=0.3, mix=0.3, damp=2500)
def j_birth():
    items, t = seq([('E5', 2 * SX), ('G5', SX), ('A5', SX), ('G5', 2 * SX), ('E5', 2 * SX), ('D5', 2 * SX), ('E5', 2 * SX)], lambda f, d: box(f, d, 0.3), 0.0, 0.5)
    items += [(t, box(fq('C6'), 0.8, 0.4), 0.45), (t, bell(fq('C6'), 0.22), 0.2), (t + 0.05, sparkle(0.4, 4, amp=0.15), 0.6)]
    items += [(0, box(fq('C4'), 0.6, 0.45), 0.2), (6 * SX, box(fq('G3'), 0.6, 0.45), 0.2), (t, box(fq('C4'), 0.8, 0.5), 0.22), (t, box(fq('E4'), 0.8, 0.5), 0.15)]
    return delay(mix(t + 1.0, items), 3 * SX, fb=0.3, mix=0.3, damp=2200)
def j_death():
    items, t = seq([('E5', 3 * SX), ('D5', SX), ('C5', 2 * SX), ('B4', 2 * SX)], lambda f, d: box(f, d, 0.32), 0.0, 0.5)
    items += [(t, box(fq('A4'), 0.9, 0.45), 0.45)]
    items += [(0, box(fq('A3'), 0.8, 0.5), 0.22), (4 * SX, box(fq('F3'), 0.8, 0.5), 0.22), (t, box(fq('A3'), 1.0, 0.55), 0.22), (t, box(fq('C4'), 1.0, 0.55), 0.14), (t, box(fq('E4'), 1.0, 0.55), 0.1)]
    return delay(mix(t + 1.1, items), 3 * SX, fb=0.3, mix=0.3, damp=2000)

# ------------------------------------------------------------------ ui
def ui_click():
    n = N(0.1); soft = bp(nz(n), 1200, 3500) * np.minimum(np.arange(n) / N(0.003), 1) * np.exp(-np.arange(n) / SR / 0.018)
    return mix(0.12, [(0, soft, 0.5), (0, g(0.02, 1500, 4000, 0.003), 0.25), (0, thump(220, 320, 0.008), 0.2)])
def ui_hover():
    n = N(0.05); return lp(tri(1180, 0.05, steps=False), 3000) * adsr(n, 0.006, 0.02, 0.4, 0.02, N(0.03)) * 0.5
def ui_tab():
    return mix(0.15, [(0, g(0.03, 1500, 4500, 0.002), 0.5), (0.01, pls(fq('G5'), 0.05), 0.4)])
def ui_open():
    n = N(0.14); sw = lp_sweep(bp(nz(n), 600, 4000), np.geomspace(1000, 3500, n)) * hump(n, 1.2) * 0.25
    return mix(0.35, [(0, sw, 1.0), (0.06, pls(fq('C5'), 0.05), 0.35), (0.12, pls(fq('G5'), 0.08), 0.4)])
def ui_close():
    n = N(0.14); sw = lp_sweep(bp(nz(n), 600, 4000), np.geomspace(3500, 1000, n)) * hump(n, 1.2) * 0.25
    return mix(0.35, [(0, sw, 1.0), (0.03, pls(fq('G5'), 0.05), 0.35), (0.09, pls(fq('C5'), 0.07), 0.4), (0.13, thump(160, 240, 0.01), 0.3)])
def ui_toggle():
    return mix(0.15, [(0, click(1200, 4500, 0.002), 0.5), (0, thump(200, 300, 0.008), 0.3), (0.02, blip(fq('E5'), fq('A5'), 0.06), 0.35)])
def ui_slider():
    items = []
    for i in range(6): items.append((i * 0.04, ping(900 * 2 ** (i / 12 * 2), 0.006, 0.03), 0.4)); items.append((i * 0.04, g(0.01, 2000, 5000, 0.001), 0.2))
    return mix(0.3, items)
def ui_banner():
    n = N(0.25); sw = lp_sweep(bp(nz(n), 500, 4000), np.geomspace(800, 3000, n)) * hump(n, 1.2) * 0.2
    return mix(0.9, [(0, sw, 1.0), (0.15, bell(fq('G5'), 0.18, 0.7), 0.35), (0.15, pls(fq('G5'), 0.05), 0.2), (0.27, bell(fq('C6'), 0.2, 0.7), 0.35), (0.27, pls(fq('C6'), 0.07), 0.2)])
def ui_digest():
    pt = page_turn()
    items, t = seq([('E5', SX), ('G5', SX), ('C6', 2 * SX)], lambda f, d: box(f, d, 0.22), 0.25, 0.45)
    return mix(t + 0.6, [(0, pt, 0.6)] + items + [(t - 2 * SX, bell(fq('C6'), 0.2, 0.7), 0.2)])
def ui_error():
    tone = lambda f, d: lp(tri(f, d + 0.06, steps=True) * 0.7 + pulse(f, d + 0.06, 0.5) * 0.15, 1500) * adsr(N(d + 0.06), 0.004, 0.05, 0.6, 0.05, N(d))
    return mix(0.4, [(0, tone(fq('E4'), 0.09), 0.6), (0.12, tone(fq('C4'), 0.14), 0.6), (0.12, thump(110, 170, 0.015), 0.2)])

def build():
    F = []
    sfx = [('page_turn', page_turn), ('book_close', book_close), ('write', quill_write), ('radio_static', radio_static), ('radio_on', radio_on),
           ('radio_off', radio_off), ('brush', brush)] + [(f'bird_{v}', (lambda v=v: bird(v))) for v in (1, 2, 3)] + [
           ('owl', owl), ('frog', frog), ('rabbit', rabbit), ('squirrel', squirrel), ('hedgehog', hedgehog), ('egg_laid', egg_laid),
           ('egg_wobble', egg_wobble), ('egg_hatch', egg_hatch), ('grow_up', grow_up), ('grow_old', grow_old), ('death_knell', death_knell),
           ('stone_placed', stone_placed)]
    F += [(f'sfx/{n}', 7001 + i, fn) for i, (n, fn) in enumerate(sfx)]
    jin = [('first', j_first), ('invention', j_invention), ('project_done', j_project_done), ('new_era', j_new_era),
           ('something_new', j_something_new), ('birth', j_birth), ('death', j_death)]
    F += [(f'jingles/{n}', 7101 + i, fn) for i, (n, fn) in enumerate(jin)]
    ui = [('click', ui_click), ('hover', ui_hover), ('tab', ui_tab), ('open', ui_open), ('close', ui_close), ('toggle', ui_toggle),
          ('slider', ui_slider), ('banner', ui_banner), ('digest', ui_digest), ('error', ui_error)]
    F += [(f'ui/{n}', 7201 + i, fn) for i, (n, fn) in enumerate(ui)]
    return F

def render(rel, fn):
    if rel.startswith('jingles/'):
        return level(trim_sfx(hp(fn(), 30), tail_keep=0.05, fade_out=0.05), -16.0)
    return level(trim_sfx(hp(fn(), 40), tail_keep=0.03, fade_out=0.02), TARGETS.get(rel, -16.0))

if __name__ == '__main__':
    only = set(sys.argv[1:])
    for d in ('sfx', 'jingles', 'ui'): os.makedirs(f'{ROOT}/{d}', exist_ok=True)
    for rel, sd, fn in build():
        if only and rel not in only and rel.split('/')[1] not in only: continue
        seed(sd); x = render(rel, fn); write(f'{ROOT}/{rel}', x)
        print(f'{rel:22s} {len(x)/SR:6.3f}s {lufs(x):6.2f} LUFS {true_peak_db(x):6.2f} dBTP', flush=True)
