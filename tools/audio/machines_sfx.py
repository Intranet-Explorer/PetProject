"""Batch 6: machines, cooking, train, sweeper, house (sfx). Procedural, retro-cozy.
Loops (exact length, -16 LUFS): noise beds rendered L+0.5 s and equal-power crossfaded at the seam;
events placed circularly (wrap); filters applied circularly; tonal motor parts built exactly periodic
(integer cycles over L) with pitch warble so no pure pitch is held > 0.3 s; then rotate to a zero
crossing + 32-sample taper (start/end exactly 0).
One-shots: render -> 40 Hz HP -> trim + 20 ms fade -> -16 LUFS, <= -1 dBTP (as batch 5)."""
import sys
from hands_sfx import g, rustle, thump, nz, seed, R, j, blip, note, bell, ping, click, sparkle, mix
from ambience_batch2 import curve, xfade_loop, circ, times, creak, grain
from ambience_batch3 import crackles
from synth import *
OUT = '/workspace/house-audio/sfx'
XF = 0.5
LOOPS = {'kiln_fire': 10, 'loom': 6, 'millstone': 8, 'stove_sizzle': 6, 'pot_bubble': 6, 'train_chug': 4, 'sweeper_whir': 4}

# ------------------------------------------------------------------ helpers
def pmod(M, fc):
    """Random smooth modulator, unit std, (circular) low-passed noise."""
    m = circ(lambda z: lp(z, fc), nz(M)); return m / (m.std() + 1e-9)
def bed(L, fn):
    """Render a non-periodic bed of L+XF seconds-worth of samples, then equal-power crossfade to L."""
    return xfade_loop(fn(L + N(XF)), L)
def hump(n, p=1.0): return np.sin(np.pi * np.arange(n) / n) ** p
def metal(f, tau=0.06, d=0.4, amp=1.0, ratios=(1.0, 1.47, 2.09, 2.56, 3.19, 4.11)):
    n = N(d); t = np.arange(n) / SR; y = np.zeros(n)
    for k, r in enumerate(ratios):
        y += (0.8 ** k) * np.sin(2 * np.pi * f * r * t + R().uniform(0, 6.28)) * np.exp(-t / (tau / (1 + 0.35 * k)))
    return lp(y * np.minimum(t / 0.0015, 1), 6000) * amp + 0.3 * g(d, 1500, 6000, 0.003)
def chirp(f0, f1, d, tau):
    n = N(d); return np.sin(2 * np.pi * np.cumsum(expsweep(f0, f1, d)) / SR) * expenv(n, tau, 0.001)
def wood(f0=420, f1=280, tau=0.014, d=0.08):
    n = N(d); return (tri(expsweep(f0, f1, d), d, steps=False) * expenv(n, tau, 0.0008)
                      + 0.5 * bp(nz(n), 400, 2500) * expenv(n, tau * 0.6, 0.0005))
def periodic_tone(L, f0, cents, wave='pulse', duty=0.3):
    """Tone with pitch contour `cents` (len L); f0 nudged so the loop holds an integer number of cycles."""
    f = f0 * 2 ** (cents / 1200); cyc = f.sum() / SR; f = f * round(cyc) / cyc
    ph = (np.cumsum(f) / SR) % 1.0
    if wave == 'pulse': return np.where(ph < duty, 1.0, -1.0) - (2 * duty - 1)
    return 4 * np.abs(ph - 0.5) - 1
def loopsin(L, cycles, phase=0.0): return np.sin(2 * np.pi * cycles * np.arange(L) / L + phase)

# ------------------------------------------------------------------ loops
def kiln_fire():
    L = N(10)
    def roar(M):
        body = lp(nz(M), 520) * np.clip(1 + 0.35 * pmod(M, 3) + 0.25 * pmod(M, 0.6), 0.15, None)
        mid = bp(nz(M), 300, 1400) * np.clip(1 + 0.5 * pmod(M, 6), 0.1, None) * 0.35
        rum = lp(nz(M), 110) * (1 + 0.3 * pmod(M, 0.4)) * 1.4
        whoosh = bp(nz(M), 500, 2200) * np.clip(pmod(M, 0.5), 0, None) ** 2 * 0.12
        return body + mid + rum + whoosh
    x = bed(L, roar)
    x += circ(lambda z: lp(z, 7000), crackles(L, 9, 0.35, big_p=0.1))
    return x
def loom():
    L = N(6); x = np.zeros(L); cyc = 1.5
    for c in range(4):
        t0 = c * cyc + j(-0.01, 0.01); a = j(0.85, 1.0)
        place(x, wood(j(430, 470), 300, 0.016), t0, a, wrap=True)                  # clack
        place(x, wood(j(380, 410), 270, 0.014), t0 + j(0.17, 0.2), a * 0.8, wrap=True)  # clack
        n = N(0.4); sw = lp_sweep(nz(n), np.linspace(900, 2600, n)) * hump(n, 1.5) * 0.035
        place(x, sw, t0 + 0.45, 1.0, wrap=True)                                      # shuttle swish
        place(x, click(1500, 4000, 0.002), t0 + 0.86, 0.35, wrap=True)              # shuttle catch
        place(x, thump(90, 150, 0.03), t0 + 1.02, 0.5, wrap=True)                   # treadle
        place(x, creak(0.25, j(30, 38), j(42, 50), [(350, 900, 1.0), (1100, 2000, 0.3)]), t0 + 1.0, 0.08, wrap=True)
    x += bed(L, lambda M: lp(nz(M), 300) * 0.012)                                    # faint room air, keeps it alive
    return x
def millstone():
    L = N(8); t = np.arange(L) / SR; rev = 4                                         # 2 s per revolution
    rot = loopsin(L, rev); rot2 = loopsin(L, rev * 2, 1.0)
    def grind(M):
        a = bp(nz(M), 180, 1100) * 0.6
        rough = bp(nz(M), 700, 2600) * np.clip(1 + 0.6 * pmod(M, 12), 0.1, None) * 0.18
        rum = lp(nz(M), 90) * 0.9
        return a + rough + rum
    x = bed(L, grind) * (1 + 0.28 * rot + 0.1 * rot2)
    gr = np.zeros(L)
    for tt in times(8, 1 / 160, 0.002, jitter=0.9):
        place(gr, grain(0.01, 1200, 4000, R().uniform(0.001, 0.003)), tt, R().uniform(0.1, 0.5) * (1.1 + 0.6 * np.sin(2 * np.pi * rev * tt / 8)), wrap=True)
    x += gr * 0.25
    for k in range(rev):
        place(x, thump(70, 120, 0.05), k * 2 + 0.35, 0.35, wrap=True)               # stone bump each revolution
        place(x, creak(0.45, j(22, 26), j(30, 36), [(250, 700, 1.0), (900, 1600, 0.3)]), k * 2 + 1.1, 0.12, wrap=True)
    return x
def stove_sizzle():
    L = N(6)
    def siz(M):
        hiss = bp(nz(M), 1200, 4500) * np.clip(1 + 0.5 * pmod(M, 14) + 0.25 * pmod(M, 1.0), 0.1, None) * 0.5
        mid = bp(nz(M), 500, 1500) * np.clip(1 + 0.6 * pmod(M, 9), 0, None) * 0.18
        pan = lp(nz(M), 160) * 0.3
        return hiss + mid + pan
    x = bed(L, siz)
    pops = np.zeros(L)
    for tt in times(6, 1 / 70, 0.003, jitter=0.95):
        lo = R().uniform(1500, 3500); place(pops, grain(0.01, lo, lo * 2.5, R().uniform(0.0006, 0.0015)), tt, R().uniform(0.2, 1.0), wrap=True)
    for tt in times(6, 0.7, 0.25):                                                   # bigger spits
        e = np.zeros(N(0.1)); k = 0.0
        for _ in range(R().integers(2, 5)): place(e, grain(0.015, 1200, 5000, R().uniform(0.002, 0.005)), N(k), R().uniform(0.5, 1)); k += R().uniform(0.005, 0.03)
        place(pops, e, tt, 1.6, wrap=True)
    return circ(lambda z: lp(z, 5500, 4), x + circ(lambda z: lp(z, 5000), pops) * 0.5)
def pot_bubble():
    L = N(6)
    x = bed(L, lambda M: lp(nz(M), 500) * np.clip(1 + 0.4 * pmod(M, 2), 0.2, None) * 0.22 + bp(nz(M), 600, 2000) * 0.025)
    for tt in times(6, 1 / 8, 0.025, jitter=0.9):
        f0 = R().uniform(180, 420); d = R().uniform(0.018, 0.04)
        place(x, chirp(f0, f0 * R().uniform(1.5, 2.3), d, d * 0.45), tt, R().uniform(0.25, 0.7), wrap=True)
    for tt in times(6, 1.1, 0.4):                                                    # big blub
        f0 = R().uniform(110, 170); d = R().uniform(0.05, 0.08)
        place(x, chirp(f0, f0 * 2.0, d, d * 0.4) + 0.4 * lp(nz(N(d)), 400) * expenv(N(d), 0.02, 0.002), tt, 0.9, wrap=True)
        place(x, g(0.03, 800, 3000, 0.006), tt + d * 0.8, 0.12, wrap=True)          # pop/splat
    return x
def train_chug():
    L = N(4); x = np.zeros(L); acc = [1.0, 0.6, 0.8, 0.6]
    for k in range(16):
        tt = k * 0.25 + j(-0.006, 0.006); n = N(0.2)
        lo = j(250, 320); ch = bp(nz(n), lo, lo * 6) * expenv(n, j(0.045, 0.06), 0.004) + 0.8 * lp(nz(n), 260) * expenv(n, 0.05, 0.004)
        place(x, ch, tt, acc[k % 4] * j(0.9, 1.0), wrap=True)
    for t0 in (0.38, 2.38):                                                           # rail joints: clickety-clack
        place(x, wood(700, 520, 0.008, 0.05) * 0.6 + metal(900, 0.02, 0.05, 0.15), t0, 0.35, wrap=True)
        place(x, wood(650, 480, 0.008, 0.05) * 0.6 + metal(850, 0.02, 0.05, 0.15), t0 + 0.14, 0.3, wrap=True)
    x += bed(L, lambda M: lp(nz(M), 140) * (1 + 0.2 * pmod(M, 1)) * 0.25 + bp(nz(M), 300, 900) * 0.02)
    x *= 1 + 0.06 * loopsin(L, 2)
    return circ(lambda z: lp(z, 5000), x)
def sweeper_whir():
    L = N(4)
    cents = 65 * loopsin(L, 22) + 25 * loopsin(L, 3, 0.7) + 35 * curve(L, L, kmax=5)   # warble + wander
    tone = periodic_tone(L, 230, cents, 'pulse', 0.35) * 0.5 + periodic_tone(L, 460, cents, 'tri') * 0.35
    tone = circ(lambda z: lp(z, 1600), tone) * (1 + 0.25 * loopsin(L, 22, 1.3)) * (1 + 0.1 * curve(L, L, kmax=4))
    x = tone * 0.35
    x += bed(L, lambda M: bp(nz(M), 1500, 5000) * np.clip(1 + 0.4 * pmod(M, 8), 0.2, None) * 0.07)     # brushes
    for k in range(32):                                                                                   # wheel/gear tick
        place(x, click(2000, 5000, 0.0012), k * 0.125 + j(-0.004, 0.004), j(0.05, 0.12), wrap=True)
    return x

# ------------------------------------------------------------------ one-shots
def kiln_door():
    hinge = creak(0.35, 60, 35, [(700, 1600, 1.0), (1800, 3000, 0.3)])
    return mix(1.2, [(0, metal(1350, 0.03, 0.2), 0.35), (0, click(1200, 4000, 0.003), 0.4), (0.08, hinge, 0.18),
                     (0.45, metal(330, 0.12, 0.6), 0.6), (0.45, thump(90, 160, 0.04), 0.7),
                     (0.53, metal(760, 0.05, 0.3), 0.25), (0.6, metal(820, 0.04, 0.25), 0.15)])
def forge_bellows():
    n = N(0.75); fc = np.concatenate([np.linspace(500, 2400, n // 2), np.linspace(2400, 700, n - n // 2)])
    air = lp_sweep(nz(n), fc) * hump(n, 1.3) * 0.5
    flare_n = N(0.8); flare = lp(nz(flare_n), 380) * hump(flare_n, 0.8) * 0.8
    cr = np.zeros(N(0.6))
    for tt in np.sort(R().uniform(0, 0.55, 12)): place(cr, grain(0.01, 1500, 5000, 0.0015), N(tt), R().uniform(0.2, 0.8))
    return mix(1.4, [(0, creak(0.3, 28, 40, [(300, 900, 1.0), (1000, 1800, 0.3)]), 0.15), (0.05, air, 1.0),
                     (0.4, flare, 1.0), (0.5, cr, 0.25), (0.75, thump(80, 130, 0.04), 0.3)])
def anvil(v):
    f0 = [880, 945, 830][v - 1] * j(0.99, 1.01)
    def ring(f, a=1.0):
        n = N(1.0); t = np.arange(n) / SR; y = np.zeros(n)
        for r, amp, tau in [(1.0, 1.0, 0.2), (2.43, 0.45, 0.11), (3.88, 0.25, 0.07), (5.3, 0.12, 0.04)]:
            y += amp * np.sin(2 * np.pi * f * r * t) * np.exp(-t / tau)
        return lp(y * np.minimum(t / 0.001, 1), 6000) * a
    hit = lambda f, a: [(0, ring(f), a), (0, click(1500, 6000, 0.002), 0.5 * a), (0, thump(120, 220, 0.015), 0.5 * a)]
    items = hit(f0, 0.6)
    if v == 3: items += [(t, x, a) for t, x, a in [(0.2 + tt, xx, aa) for tt, xx, aa in hit(f0 * 1.045, 0.38)]]
    return mix(1.2, items)
def quench():
    n = N(1.6); t = np.arange(n) / SR
    hiss = lp(lp_sweep(bp(nz(n), 1200, 4500), np.geomspace(5000, 1800, n)), 5000, 4) * np.minimum(t / 0.01, 1) * np.exp(-t / 0.35) * 0.55
    body = bp(nz(n), 400, 1500) * np.minimum(t / 0.01, 1) * np.exp(-t / 0.25) * 0.25
    b = hiss + body; k = 0.02
    while k < 1.3:
        f0 = j(180, 450); d = j(0.015, 0.035)
        place(b, chirp(f0, f0 * 1.8, d, d * 0.4), N(k), 0.3 * np.exp(-k / 0.5)); k += R().exponential(1 / 22)
    return mix(1.6, [(0, b, 1.0), (0, thump(100, 180, 0.02), 0.35), (0, metal(700, 0.02, 0.1), 0.1)])
def cook_done():
    return mix(1.0, [(0, bell(fq('A5'), 0.22, 1.0), 0.5), (0, note('A5', 0.05, 0.5), 0.15), (0.0, click(2500, 6000, 0.001), 0.2),
                     (0.09, bell(fq('E6'), 0.14, 0.7), 0.14)])
def chop():
    items = []; t = 0.0
    for i in range(4):
        items += [(t, wood(j(400, 450), 260, 0.012, 0.07), 0.8), (t, g(0.05, 1500, 5000, j(0.005, 0.008)), 0.45), (t, click(2000, 6000, 0.0015), 0.3)]
        t += j(0.14, 0.18)
    return mix(t + 0.12, items)
def stir():
    d = 1.3; n = N(d); tt = np.arange(n) / SR
    swirl = lp_sweep(bp(nz(n), 300, 3000), 1100 + 500 * np.sin(2 * np.pi * 1.6 * tt)) * hump(n, 0.7) * 0.3
    items = [(0, swirl, 1.0)]
    for k in np.sort(R().uniform(0.05, 1.1, 6)):
        f0 = j(200, 330); items.append((k, chirp(f0, f0 * 1.7, 0.035, 0.015), j(0.15, 0.3)))
    items += [(0.33, metal(2100, 0.02, 0.1), 0.12), (0.95, metal(2050, 0.02, 0.1), 0.1)]
    return mix(d + 0.05, items)
def serve():
    def clink(f, a):
        n = N(0.3); t = np.arange(n) / SR
        return a * (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.05) + 0.5 * np.sin(2 * np.pi * f * 2.32 * t) * np.exp(-t / 0.03) + 0.25 * np.sin(2 * np.pi * f * 3.7 * t) * np.exp(-t / 0.018))
    n = N(0.16); slide = bp(nz(n), 400, 1600) * hump(n, 1.2) * 0.25
    return mix(0.65, [(0, slide, 1.0), (0.14, thump(120, 200, 0.02), 0.7), (0.14, clink(j(1450, 1550), 0.35), 1.0),
                      (0.14, click(1500, 5000, 0.002), 0.3), (0.22, clink(j(1700, 1800), 0.15), 1.0)])
def works_feed():
    items = []
    for k in np.sort(R().uniform(0, 0.35, 7)):
        items.append((k, metal(j(900, 1900), j(0.02, 0.035), 0.12), j(0.15, 0.3)))
    for i, t0 in enumerate((0.45, 0.66, 0.87)):
        d = 0.16; n = N(d)
        chomp = lp(pulse(expsweep(j(150, 170), 85, d), d, 0.3), 1200) * adsr(n, 0.005, 0.06, 0.5, 0.05, n - N(0.05))
        items += [(t0, chomp, 0.4), (t0, thump(80, 150, 0.03), 0.6), (t0 + 0.02, g(0.05, 600, 3000, 0.01), 0.3)]
    d = 0.55; n = N(d); tt = np.arange(n) / SR
    f = 70 * 2 ** ((100 * np.sin(2 * np.pi * 7 * tt) + 80 * np.sin(2 * np.pi * 2.3 * tt)) / 1200)
    grind = lp(pulse(f, d, 0.4), 700) * hump(n, 0.6) * 0.4
    gr = np.zeros(n)
    for k in R().uniform(0, d - 0.02, 40): place(gr, grain(0.01, 800, 3000, 0.002), N(k), R().uniform(0.1, 0.4))
    items += [(1.0, grind, 1.0), (1.0, gr * hump(n), 0.6), (1.55, blip(300, 150, 0.1, 0.3), 0.3)]
    return mix(1.75, items)
def works_out():
    d = 0.5; n = N(d)
    whirr = lp(pulse(expsweep(150, 460, d), d, 0.25), 2000) * np.linspace(0.3, 1, n) * 0.35 + bp(nz(n), 800, 3000) * np.linspace(0, 0.1, n)
    return mix(1.5, [(0, whirr, 1.0), (0.5, metal(320, 0.08, 0.3), 0.4), (0.5, thump(90, 150, 0.035), 0.7),
                     (0.6, chirp(300, 900, 0.08, 0.04), 0.5), (0.72, thump(150, 250, 0.015), 0.5), (0.72, click(900, 3000, 0.003), 0.3),
                     (0.82, bell(fq('C6'), 0.2, 0.7), 0.25), (0.86, sparkle(0.25, 3), 0.6)])
def train_whistle():
    def toot(d, f0):
        n = N(d); t = np.arange(n) / SR
        c = (-220 * np.exp(-t / 0.03) + 60 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(t / 0.06, 1)
             + 30 * t / d - 160 * np.clip((t - (d - 0.12)) / 0.12, 0, 1) ** 2)
        y = 0
        for ratio, a in [(1.0, 1.0), (1.26, 0.6)]:
            ph = 2 * np.pi * np.cumsum(f0 * ratio * 2 ** (c / 1200)) / SR
            y = y + a * (0.7 * np.sin(ph) + 0.3 * (2 / np.pi) * np.arcsin(np.sin(ph)))
        breath = bp(nz(n), 500, 2500) * 0.15
        return lp(y + breath, 2600) * adsr(n, 0.04, 0.1, 0.85, 0.12, n - N(0.12))
    return mix(1.5, [(0, toot(0.3, 523), 0.5), (0.4, toot(0.95, 523), 0.55)])
def train_brake():
    d = 1.3; n = N(d); t = np.arange(n) / SR
    fric = bp(nz(n), 800, 3000) * np.minimum(t / 0.1, 1) * np.clip((d - t) / 0.4, 0, 1) * 0.3
    sq = tri(expsweep(1050, 640, d) * 2 ** (25 * np.sin(2 * np.pi * 7 * t) / 1200), d, steps=False)
    sq = lp(sq, 2500) * np.minimum(t / 0.2, 1) * np.clip((d - t) / 0.5, 0, 1) * 0.18
    pn = N(0.5); pssh = lp(hp(nz(pn), 2000), 6500) * np.minimum(np.arange(pn) / N(0.02), 1) * np.exp(-np.arange(pn) / SR / 0.15) * 0.3
    items = [(0, fric + sq, 1.0), (0, wood(700, 520, 0.008, 0.05), 0.25), (0.27, wood(650, 480, 0.008, 0.05), 0.2), (0.6, wood(620, 470, 0.008, 0.05), 0.15),
             (1.1, thump(90, 160, 0.04), 0.7), (1.1, metal(420, 0.05, 0.25), 0.25), (1.22, thump(100, 170, 0.03), 0.35), (1.22, pssh, 1.0)]
    return mix(1.8, items)
def train_load():
    def crate(a):
        return [(0, thump(110, 180, 0.035), 0.9 * a), (0, wood(260, 170, 0.03, 0.12), 0.5 * a), (0, g(0.06, 500, 2500, 0.01), 0.3 * a),
                (0.03, creak(0.2, 32, 42, [(400, 1200, 1.0)]), 0.08 * a)]
    items = crate(1.0) + [(0.45 + t, x, a) for t, x, a in crate(0.7)]
    for k in (0.12, 0.17, 0.55, 0.6): items.append((k, metal(j(1100, 1600), 0.02, 0.08), 0.08))
    items.append((0.75, rustle(0.25, 600, 3000), 0.4))
    return mix(1.1, items)
def sweeper_beep():
    def bip(f): n = N(0.07); return lp(pulse(f, 0.07, 0.25) * 0.5 + tri(f, 0.07) * 0.5, 4000) * adsr(n, 0.003, 0.02, 0.6, 0.03, N(0.04))
    return mix(0.42, [(0, bip(fq('A5')), 0.5), (0.0, bip(fq('A6')), 0.08), (0.17, bip(fq('A5')), 0.4), (0.17, bip(fq('A6')), 0.06)])
def sweeper_pickup():
    d = 0.38; n = N(d)
    suck = lp_sweep(nz(n), np.geomspace(500, 3500, n)) * np.linspace(0.2, 1, n) * 0.4
    motor = lp(pulse(expsweep(220, 440, d), d, 0.35), 1800) * np.linspace(0.3, 1, n) * 0.15
    items = [(0, suck + motor, 1.0), (0.38, chirp(650, 220, 0.05, 0.02), 0.5), (0.38, thump(150, 250, 0.012), 0.35)]
    for k in (0.42, 0.47, 0.5): items.append((k, metal(j(1300, 1900), 0.015, 0.06), 0.08))
    items.append((0.56, blip(660, 990, 0.08), 0.35))
    return mix(0.8, items)
def door_open():
    n = N(0.7); air = lp(nz(n), 600) * hump(n, 1.5) * 0.18
    return mix(1.3, [(0, click(1200, 4000, 0.003), 0.5), (0, metal(1150, 0.02, 0.1), 0.15), (0.02, thump(140, 220, 0.012), 0.4),
                     (0.1, creak(0.65, 46, 28, [(400, 1100, 1.0), (1300, 2600, 0.35)]), 0.4), (0.25, air, 1.0)])
def door_close():
    n = N(0.28); air = lp(nz(n), 700) * hump(n, 1.2) * 0.2
    return mix(0.85, [(0, air, 1.0), (0, creak(0.22, 34, 44, [(400, 1100, 1.0), (1300, 2600, 0.3)]), 0.25),
                      (0.26, thump(80, 140, 0.045), 1.0), (0.26, wood(220, 140, 0.035, 0.15), 0.6), (0.26, g(0.08, 300, 1500, 0.02), 0.35),
                      (0.29, click(1200, 4000, 0.003), 0.4), (0.29, metal(1100, 0.02, 0.1), 0.12), (0.36, wood(260, 180, 0.01, 0.06), 0.15)])
def gate_creak():
    return mix(1.7, [(0, creak(1.1, 26, 55, [(650, 1500, 1.0), (1700, 3000, 0.4)]), 0.45),
                     (1.12, metal(1080, 0.04, 0.3), 0.3), (1.12, click(1500, 5000, 0.002), 0.4), (1.24, metal(1120, 0.03, 0.2), 0.15),
                     (1.12, thump(140, 220, 0.015), 0.3)])
def store_put():
    return mix(0.85, [(0, creak(0.2, 50, 36, [(400, 1100, 1.0)]), 0.2), (0.12, thump(110, 190, 0.025), 0.7), (0.12, rustle(0.2, 700, 3500), 0.5),
                      (0.48, thump(130, 210, 0.02), 0.6), (0.48, wood(300, 200, 0.012, 0.07), 0.4), (0.52, blip(700, 440, 0.08), 0.3)])
def store_fetch():
    return mix(0.85, [(0, thump(130, 210, 0.02), 0.5), (0, wood(320, 220, 0.012, 0.07), 0.35), (0.03, creak(0.2, 36, 50, [(400, 1100, 1.0)]), 0.2),
                      (0.15, rustle(0.3, 600, 3500, 90), 0.8), (0.48, blip(440, 900, 0.09), 0.4), (0.48, click(900, 3000, 0.003), 0.3)])

def build():
    F = [(n, 6000 + i, fn) for i, (n, fn) in enumerate([('kiln_fire', kiln_fire), ('loom', loom), ('millstone', millstone),
         ('stove_sizzle', stove_sizzle), ('pot_bubble', pot_bubble), ('train_chug', train_chug), ('sweeper_whir', sweeper_whir)])]
    F += [(f'anvil_{v}', 6020 + v, (lambda v=v: anvil(v))) for v in (1, 2, 3)]
    one = [('kiln_door', kiln_door), ('forge_bellows', forge_bellows), ('quench', quench), ('cook_done', cook_done), ('chop', chop),
           ('stir', stir), ('serve', serve), ('works_feed', works_feed), ('works_out', works_out), ('train_whistle', train_whistle),
           ('train_brake', train_brake), ('train_load', train_load), ('sweeper_beep', sweeper_beep), ('sweeper_pickup', sweeper_pickup),
           ('door_open', door_open), ('door_close', door_close), ('gate_creak', gate_creak), ('store_put', store_put), ('store_fetch', store_fetch)]
    F += [(n, 6101 + i, fn) for i, (n, fn) in enumerate(one)]
    return F

def render(name, fn):
    if name in LOOPS:
        x = fn(); L = N(LOOPS[name]); assert len(x) == L, (name, len(x))
        x = circ(lambda z: hp(z, 40), x)
        e = np.convolve(np.concatenate([x[-N(0.02):], x, x[:N(0.02)]]) ** 2, np.ones(N(0.04)), 'same')[N(0.02):-N(0.02)]
        x, _ = loop_finalize(x, near=int(np.argmin(e))); x = level(x, -16.0)   # seam at the quietest moment
    else:
        x = level(trim_sfx(hp(fn(), 40), tail_keep=0.03, fade_out=0.02), -16.0)
    return x

if __name__ == '__main__':
    only = set(sys.argv[1:])
    for name, sd, fn in build():
        if only and name not in only: continue
        seed(sd); x = render(name, fn)
        write(f'{OUT}/{name}', x)
        print(f'{name:16s} {len(x)/SR:6.3f}s {lufs(x):6.2f} LUFS {true_peak_db(x):6.2f} dBTP', flush=True)
