"""Batch 9 (final): needs, getting along, conflict, the visitor (sfx). Procedural, retro-cozy,
cartoon-dramatic for conflict (no realistic gore). All hob vocals use hob_voice.py (same voice:
BASE 480 Hz, formant scale 1.18). The visitor (owner of the world) uses the SAME babble engine with
a different voice: base 210 Hz, formant scale 0.9 (larger), squarer duty 0.45, darker low-pass.
Loops argue/scuffle: exactly 4 s, events placed circularly, beds crossfaded, rotated to the quietest
point + 32-sample taper, -16 LUFS. One-shots: 40 Hz HP -> trim + 20 ms fade -> -16 LUFS, <= -1 dBTP."""
import sys
import hob_voice as HV
from hob_voice import syl, voiced, babble, breath_noise, BASE
from hob_sfx import rough, step, cat
from hands_sfx import g, rustle, thump, nz, seed, R, j, blip, note, bell, ping, click, sparkle, mix
from machines_sfx import metal, chirp, wood, hump, pmod, bed, loopsin
from ambience_batch2 import xfade_loop, circ, times
from synth import *
OUT = '/workspace/house-audio/sfx'
LOOPS = {'argue': 4, 'scuffle': 4}

def env(n, a=0.006, r=0.03): return adsr(n, a, 0.05, 0.85, r, n - N(r))
def vo(cents, path, breath=0.08, amp=1.0, a=0.006, r=0.03):
    n = len(cents); return voiced(cents, path, breath) * env(n, a, r) * amp
def gl(d, c0, c1, wob=0.0, rate=6.0):
    n = N(d); t = np.arange(n) / SR; return np.linspace(c0, c1, n) + wob * np.sin(2 * np.pi * rate * t)

# ------------------------------------------------------------------ visitor voice (distinct)
VIS_BASE, VIS_FS = 210.0, 0.90
def visitor_babble(seed_, n_syl=8, max_s=1.85):
    old = HV.FS; HV.FS = VIS_FS
    try:
        HV.seed(seed_); out = []; t = 0.0; off = 0.0
        for i in range(n_syl):
            last = i == n_syl - 1; dur = R().uniform(0.1, 0.18) if not last else 0.22
            off = np.clip(off + R().uniform(1.0, 2.5) * R().choice([-1, 1]), -3, 3.5); decl = -1.5 * i / max(1, n_syl - 1)
            n = N(dur); kind = 'fall' if last else R().choice(['rise', 'fall', 'arch', 'flat'])
            c = (off + decl) * 100 + HV.contour(n, kind, 2.5 if last else R().uniform(1, 2.5))
            v = R().choice(list(HV.VOWEL_W), p=list(HV.VOWEL_W.values()))
            y = HV.voiced(c, [(0, v)], breath=0.05, duty=0.45, base=VIS_BASE)
            y = lp(y, 3200) * adsr(n, 0.012, dur * 0.5, 0.8, 0.04, n - N(0.04))
            if t + dur > max_s: break
            out.append((t, y)); t += dur + R().uniform(0.03, 0.06) + (0.08 if R().random() < 0.2 and not last else 0)
    finally:
        HV.FS = old
    b = np.zeros(N(t + 0.1))
    for tt, y in out: place(b, y, tt)
    return b

# ------------------------------------------------------------------ needs
def tummy_rumble():
    d = 1.3; n = N(d); t = np.arange(n) / SR
    fc = 120 * 2 ** (0.9 * np.sin(2 * np.pi * 1.3 * t) + 0.5 * np.sin(2 * np.pi * 3.1 * t + 1))
    gr = lp_sweep(nz(n), fc * 3) * hump(n, 0.8) * (0.6 + 0.4 * np.clip(pmod(n, 6), -1, 1))
    items = [(0, lp(gr, 500), 1.0)]
    for k in np.sort(R().uniform(0.1, 1.1, 6)): f = j(90, 200); items.append((k, chirp(f, f * 1.8, 0.05, 0.02), j(0.15, 0.3)))
    return mix(d + 0.05, items)
def shiver():
    n = N(0.6); brr = rough(vo(gl(0.6, 100, -150, 60, 9), [(0, 'u'), (1, 'u')], 0.15), 30, 0.6)
    items = [(0, brr, 0.8)]
    for k in np.arange(0.02, 0.62, 0.055): items.append((k + j(-0.005, 0.005), click(2500, 6000, 0.001), j(0.15, 0.3)))   # teeth chatter
    return mix(0.7, items)
def sneeze():
    a1 = vo(gl(0.12, 0, 300), [(0, 'a')], 0.2, 0.6); a2 = vo(gl(0.14, 200, 500), [(0, 'a')], 0.2, 0.75)
    nb = N(0.12); burst = bp(nz(nb), 1500, 6500) * np.exp(-np.arange(nb) / SR / 0.035) * 0.9
    choo = vo(gl(0.18, 500, -400), [(0, 'u'), (1, 'u')], 0.3, 1.0)
    return mix(1.0, [(0, breath_noise(0.1, 700, 3000, 'sin', 'a'), 0.3), (0.1, a1, 1.0), (0.27, a2, 1.0), (0.55, burst, 1.0), (0.56, choo, 0.9)])
def cough():
    items = []; t = 0.0
    for i in range(3):
        nb = N(0.09); b = HV.formant(nz(nb), 'a') * np.exp(-np.arange(nb) / SR / 0.03)
        items += [(t, b, 0.8 - 0.15 * i), (t + 0.005, vo(gl(0.07, -200 - 100 * i, -500), [(0, 'a')], 0.3), 0.5 - 0.1 * i)]; t += j(0.16, 0.2)
    return mix(t + 0.1, items)

# ------------------------------------------------------------------ getting along (voiced)
def agree():
    m = vo(gl(0.12, 0, 150), [(0, 'm')], 0.06, 0.9)
    h = syl(0.16, 3.0, 'e', 'rise', 3.0, 'noise', 1.0)
    return cat(m, h, gap=0.05)
def disagree():
    a = syl(0.12, 1.0, 'u', 'fall', 2.0, 'none', 0.9, breath=0.1)
    b = syl(0.17, -1.0, 'u', 'fall', 3.5, 'nasal', 1.0, breath=0.1)
    return cat(a, b, gap=0.06)
def whisper():
    HV.seed(int(R().integers(1 << 30))); items = []; t = 0.0
    for i in range(int(R().integers(8, 12))):
        d = j(0.06, 0.13); v = R().choice(list(HV.VOWEL_W))
        x = HV.formant(nz(N(d)), v) * hump(N(d), 0.8)
        if R().random() < 0.3: items.append((t, hp(nz(N(0.05)), 4000) * hump(N(0.05)) * 0.6, 1.0)); t += 0.04    # 's'
        items.append((t, x, j(0.6, 1.0))); t += d + j(0.02, 0.06)
    return lp(mix(t + 0.05, items), 7000)
def nuzzle():
    mm = vo(gl(0.5, -100, 100, 70, 4.5), [(0, 'm')], 0.1, 0.8, 0.05, 0.12)
    return mix(0.85, [(0, rustle(0.6, 600, 3000, 50), 0.6), (0.15, mm, 0.6), (0.6, note('E6', 0.05), 0.12), (0.66, note('G6', 0.07), 0.1)])
def friend_made():
    items = [(0, note('C5', 0.08), 0.35), (0.09, note('E5', 0.08), 0.35), (0.18, note('G5', 0.08), 0.35),
             (0.27, bell(fq('C6'), 0.22), 0.4), (0.27, bell(fq('E6'), 0.18), 0.22), (0.27, note('C6', 0.12), 0.25), (0.3, sparkle(0.4, 5, amp=0.18), 1.0)]
    return mix(1.2, items)
def rival_made():
    def wah(f0, f1, d, dep=60):
        n = N(d); t = np.arange(n) / SR; f = expsweep(f0, f1, d) * 2 ** (dep * np.sin(2 * np.pi * 6 * t) / 1200)
        return lp_sweep(pulse(f, d, 0.35), np.linspace(2500, 700, n)) * env(n, 0.01, 0.06)
    return mix(0.95, [(0, wah(fq('B4'), fq('B4') * 0.98, 0.18), 0.35), (0.2, wah(fq('F4'), fq('F4') * 0.97, 0.18), 0.35),
                      (0.42, wah(fq('Bb3') * 1.03, fq('Bb3') * 0.85, 0.4), 0.4), (0.42, thump(80, 130, 0.04), 0.4)])
def apologise():
    a = vo(gl(0.2, -200, -450, 30, 5), [(0, 'o'), (1, 'o')], 0.14, 0.8, 0.02, 0.06)
    b = vo(gl(0.25, -350, -750, 30, 5), [(0, 'i'), (0.4, 'e'), (1, 'u')], 0.14, 0.75, 0.02, 0.08)
    return cat(a, b, gap=0.06)
def forgive():
    m = vo(gl(0.16, -100, 200), [(0, 'm')], 0.08, 0.8)
    a = syl(0.2, 2.5, 'a', 'arch', 3.0, 'none', 1.0, vowel2='u')
    v = cat(m, a, gap=0.04)
    return mix(len(v) / SR + 0.55, [(0, v, 1.0), (len(v) / SR - 0.05, bell(fq('G5'), 0.2, 0.6), 0.2), (len(v) / SR + 0.05, bell(fq('C6'), 0.2, 0.5), 0.2)])
def huff():
    glare = lp(pulse(fq('C3') * 2 ** (gl(0.22, 0, -60) / 1200), 0.22, 0.25), 900) * env(N(0.22), 0.02, 0.06)
    hmph = rough(vo(gl(0.12, -300, -600), [(0, 'm')], 0.1, 1.0), 34, 0.4)
    nb = N(0.2); puff = bp(nz(nb), 900, 4000) * np.minimum(np.arange(nb) / N(0.01), 1) * np.exp(-np.arange(nb) / SR / 0.06)
    return mix(0.75, [(0, glare, 0.3), (0.25, hmph, 0.9), (0.36, puff, 0.6)])

# ------------------------------------------------------------------ conflict
def whoosh(d=0.15, f0=700, f1=3000):
    n = N(d); return lp_sweep(bp(nz(n), 400, 5000), np.geomspace(f0, f1, n)) * hump(n, 1.2)
def thwack(big=1.0):
    return mix(0.3, [(0, g(0.04, 900, 5000, 0.006), 0.7 * big), (0, thump(80, 170, 0.035), 1.0), (0, chirp(420 * big ** -0.3, 160, 0.08, 0.03), 0.4),
                     (0, lp(nz(N(0.12)), 600) * expenv(N(0.12), 0.03, 0.001), 0.5)])
def shove():
    return mix(0.6, [(0, whoosh(0.16, 600, 2200), 0.35), (0.14, thump(100, 180, 0.03), 0.9), (0.14, rustle(0.15, 600, 3000), 0.4),
                     (0.24, g(0.15, 800, 3000, 0.04), 0.2)])
def snatch():
    return mix(0.55, [(0, whoosh(0.12, 900, 4000), 0.4), (0.1, click(1200, 4000, 0.003), 0.6), (0.1, rustle(0.1, 900, 4000), 0.4),
                      (0.14, blip(500, 1400, 0.12, 0.25), 0.35)])
def hit(v):
    base = [1.0, 0.9, 1.15][v - 1]
    items = [(0, thwack(base), 1.0), (0.0, ping(j(1800, 2400), 0.01), 0.15)]
    if v == 3: items += [(0.12, thwack(0.8), 0.6)]
    return mix(0.45, items)
def injured():
    n = N(0.22); t = np.arange(n) / SR
    yelp = voiced(700 * np.exp(-t / 0.05) + gl(0.22, 600, -100, 50, 12), [(0, 'i'), (0.4, 'a'), (1, 'a')], 0.15) * env(n, 0.004, 0.05)
    return mix(0.6, [(0, thwack(1.0), 1.0), (0.1, yelp, 0.9)])
def killing_blow():
    items = [(0, whoosh(0.18, 500, 2500), 0.35), (0.17, thwack(1.4), 1.0), (0.17, thump(45, 90, 0.08), 1.0),
             (0.17, g(0.08, 300, 2000, 0.02), 0.6), (0.18, metal(220, 0.05, 0.2), 0.12)]
    x = mix(0.45, items); cut = N(0.38); f = N(0.006)
    x[cut - f:cut] *= np.linspace(1, 0, f) ** 2; x[cut:] = 0          # intentional hard cut to silence
    return x[:cut + N(0.02)]
def splat():
    items = [(0, lp(nz(N(0.08)), 1800) * expenv(N(0.08), 0.02, 0.001), 0.8), (0, chirp(350, 120, 0.06, 0.02), 0.6)]
    for _ in range(6): f = j(900, 1600); items.append((j(0.04, 0.25), chirp(f, f * 0.6, 0.03, 0.01), j(0.15, 0.35)))   # droplets
    return mix(0.4, items)
def bandage():
    items = []; t = 0.0
    for i in range(3):
        n = N(0.22); items.append((t, bp(nz(n), 900, 4000) * hump(n, 1.0) * 0.4, 1.0)); t += 0.24
    rip = np.zeros(N(0.12))
    for k in np.linspace(0, 0.1, 20): place(rip, g(0.008, 1500, 5000, 0.002), N(k), j(0.4, 1.0))
    items += [(t, rip, 0.6), (t + 0.18, thump(160, 240, 0.012), 0.4), (t + 0.26, thump(160, 240, 0.012), 0.35)]
    return mix(t + 0.4, items)
def limp_step():
    return mix(0.85, [(0, step('wood'), 1.0), (0.16, g(0.25, 500, 2200, 0.08) * 0.5, 0.5), (0.48, step('wood'), 0.55)])
def shunned():
    items = [(0, note('E5', 0.14, 0.25), 0.35), (0.16, note('C5', 0.14, 0.25), 0.3), (0.32, note('A4', 0.3, 0.25), 0.28)]
    x = mix(1.0, items); n = len(x); t = np.arange(n) / SR
    x = lp_sweep(x, np.geomspace(4000, 500, n)) * np.clip(1 - t / 1.0, 0, 1) ** 1.5
    return x + 0.05 * lp(nz(n), 400) * np.exp(-t / 0.4)
def driven_out():
    return mix(0.9, [(0, whoosh(0.18, 600, 2000), 0.3), (0.17, thump(60, 120, 0.06), 1.0), (0.17, wood(200, 120, 0.05, 0.2), 0.7),
                     (0.17, g(0.12, 200, 1500, 0.03), 0.5), (0.2, metal(1000, 0.03, 0.15), 0.15), (0.26, metal(1100, 0.02, 0.1), 0.1),
                     (0.3, thump(70, 120, 0.04), 0.2), (0.42, thump(70, 120, 0.04), 0.08)])
def vengeance_oath():
    def low(nm, d, a=0.4):
        n = N(d + 0.15); f = fq(nm) * 2 ** (40 * np.sin(2 * np.pi * 5 * np.arange(n) / SR) / 1200)
        return lp(pulse(f, n / SR, 0.5), 1200) * expenv(n, 0.15, 0.01) * a
    items = []; t = 0.0
    for nm, d in [('Eb4', 0.3), ('G4', 0.12), ('Ab4', 0.22), ('G4', 0.4)]:
        items.append((t, low(nm, d), 1.0)); t += d
    items += [(0, thump(50, 90, 0.08), 0.6), (t - 0.4, thump(45, 80, 0.1), 0.7), (t - 0.4, bell(fq('C3'), 0.3, 1.2), 0.25),
              (0, lp(tri(fq('C2'), 1.6), 400) * expenv(N(1.6), 0.3, 0.05), 0.45)]
    return mix(t + 0.8, items)

# ------------------------------------------------------------------ visitor & teaching
def visitor_arrives():
    items = []
    for i, nm in enumerate(['C4', 'E4', 'G4', 'C5', 'E5']): items.append((i * 0.07, note(nm, 0.08, 0.5), 0.3))
    items += [(0.4, bell(fq('E5'), 0.2), 0.45), (0.75, bell(fq('C5'), 0.22), 0.5), (0.4, sparkle(0.6, 6, amp=0.15), 1.0),
              (0.0, lp(nz(N(0.6)), 900) * hump(N(0.6), 1.5), 0.1)]
    return mix(1.6, items)
def visitor_talk():
    return visitor_babble(int(R().integers(1 << 30)), int(R().integers(6, 9)))
def hob_answers():
    return babble(int(R().integers(1 << 30)), 'statement', max_s=1.4, n_syl=6)
def teach():
    items = [(0, click(1500, 4000, 0.003), 0.4), (0.08, click(1500, 4000, 0.003), 0.35)]
    for i, nm in enumerate(['C5', 'E5', 'G5']): items.append((0.2 + i * 0.12, note(nm, 0.09, 0.25), 0.35))
    items += [(0.56, bell(fq('C6'), 0.2, 0.7), 0.3), (0.58, sparkle(0.3, 4, amp=0.15), 1.0)]
    return mix(1.1, items)
def praise():
    return mix(0.9, [(0, sparkle(0.5, 8, amp=0.3), 1.0), (0.0, bell(fq('E6'), 0.16, 0.6), 0.2), (0.12, bell(fq('G6'), 0.15, 0.6), 0.18),
                     (0, hp(nz(N(0.6)), 5000) * expenv(N(0.6), 0.15, 0.01), 0.03)])
def scold():
    def buzz(f0, f1, d):
        n = N(d); f = expsweep(f0, f1, d)
        return lp(rough(pulse(f, d, 0.5), 28, 0.35), 900) * env(n, 0.01, 0.04)
    return mix(0.4, [(0, buzz(170, 150, 0.13), 0.5), (0.17, buzz(140, 110, 0.16), 0.5)])
def gift():
    return mix(0.55, [(0, chirp(300, 900, 0.06, 0.025), 0.7), (0, g(0.03, 1500, 5000, 0.004), 0.4), (0.06, sparkle(0.25, 4, amp=0.2), 1.0)])
def suggest():
    return mix(0.6, [(0, ping(fq('A5'), 0.02, 0.2), 0.5), (0, bell(fq('A5'), 0.18, 0.55), 0.3), (0.0, click(2000, 5000, 0.001), 0.2)])
def step_in():
    def toot(d):
        n = N(d); t = np.arange(n) / SR; f = 1250 * 2 ** (gl(d, 30, -40) / 1200)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 32 * t)))   # pea-whistle trill
        return lp(x + 0.15 * bp(nz(n), 1000, 3000), 3000) * env(n, 0.008, 0.03)
    return mix(0.55, [(0, toot(0.12), 0.4), (0.17, toot(0.26), 0.45)])

# ------------------------------------------------------------------ loops (4 s)
def argue():
    L = N(4); x = np.zeros(L); t = 0.0; who = 0
    while t < 3.85:                                      # two hobs (same voice), short angry bursts, overlapping
        k = int(R().integers(2, 5)); off = (2.0 if who else -1.0)
        for i in range(k):
            d = R().uniform(0.07, 0.12)
            y = syl(d, off + R().uniform(-1, 3), None, R().choice(['fall', 'arch']), R().uniform(2, 4), R().choice(['none', 'noise', 'blip']), 1.2, breath=0.12)
            place(x, rough(y, 34, 0.3), t, 1.0, wrap=True); t += len(y) / SR + R().uniform(0.015, 0.03)
        t += R().uniform(-0.05, 0.05); who ^= 1
    x += bed(L, lambda M: bp(nz(M), 500, 2500) * 0.01)
    return x
def scuffle():
    L = N(4)
    x = bed(L, lambda M: bp(nz(M), 300, 2500) * np.clip(1 + 0.6 * pmod(M, 6), 0.2, None) * 0.12)   # dust cloud
    for tt in times(4, 0.28, 0.12):
        place(x, thwack(R().uniform(0.8, 1.2)), tt, R().uniform(0.4, 0.8), wrap=True)
    for tt in times(4, 0.5, 0.3):
        place(x, whoosh(0.1, 800, 3000), tt, 0.2, wrap=True)
    for tt in times(4, 0.9, 0.6):                         # grunts (hob voice)
        place(x, rough(syl(0.09, R().uniform(-2, 2), R().choice(['a', 'u']), 'fall', 3, 'none', 1.0, breath=0.15), 34, 0.3), tt, 0.35, wrap=True)
    for tt in times(4, 1.3, 0.9):                         # cartoon star tinkles
        place(x, ping(fq(R().choice(['C6', 'E6', 'G6'])), 0.03, 0.15), tt, 0.12, wrap=True)
    return x

def build():
    F = [('tummy_rumble', tummy_rumble), ('shiver', shiver), ('sneeze', sneeze), ('cough', cough), ('agree', agree), ('disagree', disagree),
         ('whisper', whisper), ('nuzzle', nuzzle), ('friend_made', friend_made), ('rival_made', rival_made), ('apologise', apologise),
         ('forgive', forgive), ('huff', huff), ('argue', argue), ('shove', shove), ('snatch', snatch)]
    F += [(f'hit_{v}', (lambda v=v: hit(v))) for v in (1, 2, 3)]
    F += [('injured', injured), ('scuffle', scuffle), ('killing_blow', killing_blow), ('splat', splat), ('bandage', bandage),
          ('limp_step', limp_step), ('shunned', shunned), ('driven_out', driven_out), ('vengeance_oath', vengeance_oath),
          ('visitor_arrives', visitor_arrives), ('visitor_talk', visitor_talk), ('hob_answers', hob_answers), ('teach', teach),
          ('praise', praise), ('scold', scold), ('gift', gift), ('suggest', suggest), ('step_in', step_in)]
    return [(n, 9001 + i, fn) for i, (n, fn) in enumerate(F)]

def render(name, fn):
    if name in LOOPS:
        x = fn(); L = N(LOOPS[name]); assert len(x) == L
        x = circ(lambda z: hp(z, 40), x)
        e = np.convolve(np.concatenate([x[-N(0.02):], x, x[:N(0.02)]]) ** 2, np.ones(N(0.04)), 'same')[N(0.02):-N(0.02)]
        x, _ = loop_finalize(x, near=int(np.argmin(e)))
        return level(x, -16.0)
    if name == 'killing_blow':                            # keep the hard cut: no extra tail/fade beyond the 6 ms one
        return level(trim_sfx(hp(fn(), 40), tail_keep=0.005, fade_out=0.004), -16.0)
    return level(trim_sfx(hp(fn(), 40), tail_keep=0.03, fade_out=0.02), -16.0)

if __name__ == '__main__':
    only = set(sys.argv[1:])
    for name, sd, fn in build():
        if only and name not in only: continue
        seed(sd); x = render(name, fn); write(f'{OUT}/{name}', x)
        print(f'{name:16s} {len(x)/SR:6.3f}s {lufs(x):6.2f} LUFS {true_peak_db(x):6.2f} dBTP', flush=True)
