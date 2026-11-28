"""Batch 5: hands, making, building, gathering (sfx). Procedural, retro-cozy: pulse/triangle blips,
noise textures, decaying bell tones (fundamental tau <= 0.24 s so the 6 dB sustain rule stays < 0.3 s).
Each file: render -> 40 Hz high-pass -> trim lead/trail + 20 ms fade -> -16 LUFS integrated, <= -1 dBTP."""
import sys
from hob_sfx import g, rustle, thump, nz, seed, R
from synth import *
OUT = '/workspace/house-audio/sfx'

def j(a, b): return R().uniform(a, b)
def blip(f0, f1, d, duty=0.25, a=0.004):
    n = N(d); return lp(pulse(expsweep(f0, f1, d), d, duty), 5000) * adsr(n, a, d * 0.4, 0.6, d * 0.3, n - N(d * 0.3))
def note(name, d, duty=0.25, amp=1.0):
    n = N(d + 0.03); return lp(pulse(fq(name), n / SR, duty), 4500) * adsr(n, 0.003, 0.03, 0.7, 0.03, N(d)) * amp
def bell(f, tau=0.22, d=1.2):
    n = N(d); t = np.arange(n) / SR; y = np.zeros(n)
    for ratio, a, tr in [(1.0, 1.0, tau), (2.0, 0.25, tau * 0.6), (2.76, 0.2, tau * 0.45), (5.4, 0.08, tau * 0.25)]:
        y += a * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t / tr)
    return y * np.minimum(t / 0.002, 1) + 0.15 * hp(nz(n), 4000) * np.exp(-t / 0.003)
def ping(f, tau=0.015, d=0.09):
    n = N(d); return tri(f, d, steps=False) * expenv(n, tau, 0.0005)
def click(lo=2000, hi=6000, tau=0.002, d=0.09): return g(d, lo, hi, tau)
def sparkle(dur, n_notes=8, lo='C6', amp=0.25):
    b = np.zeros(N(dur + 0.3)); pent = ['C6', 'D6', 'E6', 'G6', 'A6', 'C7']
    t = 0.0; last = None
    for i in range(n_notes):
        nm = R().choice([p for p in pent if p != last]); last = nm
        place(b, lp(pulse(fq(nm), 0.05, 0.125), 6000) * expenv(N(0.05), 0.015, 0.001), t, amp * (1 - i / (n_notes + 2))); t += dur / n_notes
    return b
def mix(dur, items):
    b = np.zeros(N(dur))
    for t, x, a in items: place(b, x, float(t), a)
    return b

def pickup():
    f = j(380, 460); return mix(0.3, [(0, rustle(0.08, 900, 4000), 0.5), (0.0, click(1500, 5000, 0.002), 0.4),
                                       (0.02, blip(f, f * j(2.1, 2.5), j(0.07, 0.09)), 0.5)])
def drop():
    f = j(850, 980); land = j(0.1, 0.14)
    return mix(0.45, [(0, blip(f, f * 0.4, j(0.09, 0.11)), 0.45), (land, thump(110, j(180, 220), 0.02), 0.8),
                      (land, click(800, 3000, 0.004), 0.4), (land + j(0.08, 0.11), thump(140, 230, 0.012), 0.25)])
def put_away():
    n = N(0.25); slide = bp(nz(n), 400, 2000) * np.sin(np.pi * np.arange(n) / n) ** 1.2 * 0.3
    return mix(0.75, [(0, slide, 1.0), (0.24, thump(120, 200, 0.022), 0.7), (0.24, click(700, 2500, 0.004), 0.4),
                      (0.48, thump(150, 250, 0.015), 0.5), (0.48, click(900, 3000, 0.003), 0.35)])
def take_out():
    return mix(0.6, [(0, thump(150, 250, 0.015), 0.5), (0, click(900, 3000, 0.003), 0.35), (0.1, rustle(0.25, 700, 3500), 0.7),
                     (0.3, blip(420, 1000, 0.09), 0.45)])
def give():
    n = N(0.22); sw = bp(nz(n), 800, 3500) * np.sin(np.pi * np.arange(n) / n) ** 2 * 0.3
    return mix(0.6, [(0, sw, 1.0), (0.18, note('G5', 0.07), 0.45), (0.27, note('C6', 0.13), 0.5)])
def make():
    b = []; t = 0.0
    for i in range(int(R().integers(4, 8))):
        if R().random() < 0.6: x = ping(j(1500, 3000), j(0.01, 0.02)) * 0.6 + click(2000, 6000, 0.0015)
        else: x = thump(j(200, 260), j(300, 380), 0.012) * 0.6 + click(700, 2500, 0.003)
        b.append((t, x, j(0.5, 1.0))); t += j(0.08, 0.22)
    return mix(t + 0.15, b)
def combine():
    return mix(0.65, [(0, click(2000, 6000, 0.002), 0.6), (0.0, ping(2200, 0.01), 0.3), (0.12, click(2000, 6000, 0.002), 0.6),
                      (0.12, ping(2600, 0.01), 0.3), (0.26, click(1200, 5000, 0.004) + ping(1700, 0.02) * 0.6 + thump(180, 300, 0.01) * 0.5, 1.0),
                      (0.3, note('E5', 0.06), 0.35), (0.37, note('A5', 0.1), 0.4)])
def unmake():
    pop = np.sin(2 * np.pi * np.cumsum(expsweep(950, 280, 0.07)) / SR) * expenv(N(0.07), 0.025, 0.001) + 0.5 * g(0.07, 1000, 5000, 0.004)
    items = [(0, pop, 0.8)] + [(0.08 + j(0, 0.35), click(1500, 6000, j(0.001, 0.003)) + ping(j(1500, 3000), 0.008) * 0.4, j(0.3, 0.6)) for _ in range(6)]
    items += [(0.12, blip(800, 380, 0.14), 0.35)]
    return mix(0.7, items)
def invent():
    items = []; t = 0.0
    for nm in ['C5', 'E5', 'G5', 'C6', 'E6']:
        items.append((t, note(nm, 0.055), 0.4)); t += 0.045
    items += [(t, bell(fq('G6'), 0.22), 0.4), (t + 0.06, bell(fq('C7'), 0.18), 0.25), (t, bell(fq('C6'), 0.24), 0.3),
              (t + 0.05, sparkle(0.7, 10), 1.0), (t, hp(nz(N(0.8)), 6000) * expenv(N(0.8), 0.2, 0.01), 0.04)]
    return mix(1.6, items)
def design():
    b = []; t = 0.0
    for i in range(int(R().integers(4, 7))):
        d = j(0.1, 0.28); n = N(d)
        grit = np.zeros(n); k = 0.0
        while k < d:
            place(grit, g(0.006, 2500, 7000, 0.0015), N(k), j(0.3, 1.0)); k += j(0.003, 0.009)
        stroke = (bp(nz(n), 2000, 6000) * 0.3 + grit * 0.6) * np.sin(np.pi * np.arange(n) / n) ** 0.8
        b.append((t, stroke, j(0.6, 1.0))); t += d + j(0.04, 0.12)
    return mix(t + 0.05, b)
def design_works():
    return mix(1.1, [(0, bell(fq('G5'), 0.22), 0.45), (0, note('G5', 0.08, 0.5), 0.2), (0.14, bell(fq('C6'), 0.24), 0.5),
                     (0.14, note('C6', 0.1, 0.5), 0.2), (0.16, sparkle(0.35, 5), 0.6)])
def design_fails():
    items = []; t = 0.0
    for i in range(6):                                     # sputter
        items.append((t, g(j(0.02, 0.05), 300, 3000, j(0.005, 0.012)), j(0.4, 0.8))); t += j(0.05, 0.1)
    n = N(0.5); tt = np.arange(n) / SR
    womp = lp(pulse(expsweep(520, 140, 0.5) * (1 + 0.06 * np.sin(2 * np.pi * 9 * tt)), 0.5, 0.3), 2500) * adsr(n, 0.01, 0.2, 0.8, 0.1, n - N(0.1))
    items.append((0.1, womp, 0.45))
    fz = N(0.45); items.append((0.4, hp(nz(fz), 2500) * expenv(fz, 0.12, 0.01), 0.18))     # fizzle
    items += [(0.75, thump(70, 140, 0.04), 1.0), (0.75, ping(620, 0.05, 0.25) * 0.5 + ping(910, 0.035, 0.25) * 0.35 + click(500, 2500, 0.006, 0.25), 0.7)]  # clunk
    return mix(1.25, items)
def hammer(double=False):
    def hit():
        return (click(1000, 5000, 0.0025, 0.1) * 0.7 + tri(expsweep(j(300, 340), j(170, 200), 0.1), 0.1, steps=False) * expenv(N(0.1), 0.022, 0.001)
                + 0.6 * lp(nz(N(0.1)), 600) * expenv(N(0.1), 0.02, 0.001) + 0.3 * ping(j(2300, 2800), 0.01, 0.1))
    items = [(0, hit(), 1.0)] + ([(j(0.17, 0.22), hit(), 0.6)] if double else [])
    return mix(0.45, items)
def saw():
    items = []; t = 0.0
    for i in range(4):
        d = j(0.3, 0.38); n = N(d); push = i % 2 == 0
        rasp = np.zeros(n); k = 0.0; rate = j(45, 70)
        while k < d:
            place(rasp, g(0.008, 1500, 6000, 0.002), N(k), j(0.5, 1.0)); k += (1 / rate) * j(0.6, 1.4)
        fcs = np.linspace(1500, 3000, n) if push else np.linspace(2600, 1400, n)
        body = lp_sweep(nz(n), fcs) * 0.6
        items.append((t, (rasp * 0.5 + body) * np.sin(np.pi * np.arange(n) / n) ** 0.7, 1.0 if push else 0.75)); t += d + 0.02
    return mix(t + 0.05, items)
def build_done():
    items = [(0, hammer(), 0.7)]; t = 0.18
    for nm in ['C5', 'E5', 'G5', 'C6']:
        items.append((t, note(nm, 0.07, 0.5), 0.4)); t += 0.07
    items += [(t, bell(fq('C6'), 0.24), 0.45), (t, bell(fq('G6'), 0.2), 0.3), (t, note('C6', 0.12, 0.25), 0.3), (t + 0.05, sparkle(0.6, 8), 0.8)]
    return mix(1.7, items)
def mend():
    items = []; t = 0.0
    for i in range(3):
        n = N(0.12); zp = lp_sweep(nz(n), np.linspace(1000, 4500, n)) * np.sin(np.pi * np.arange(n) / n) * 0.8
        items += [(t, zp, 1.0), (t + 0.13, click(2500, 7000, 0.0015), 0.3)]; t += j(0.2, 0.26)
    items += [(t + 0.02, bell(fq('E6'), 0.15, 0.6), 0.3)]
    return mix(t + 0.5, items)
def gather():
    snap = click(1500, 5000, 0.002) + ping(j(900, 1300), 0.006) * 0.4
    return mix(0.6, [(0, rustle(j(0.25, 0.35), 700, 4000, 90), 0.8), (j(0.12, 0.2), snap, 0.9),
                     (j(0.25, 0.3), blip(j(500, 600), 1100, 0.07), 0.25)])
def water_plants():
    d = 1.6; n = N(d); t = np.arange(n) / SR
    fast = np.clip(1 + 0.4 * lp(nz(n), 25) * 6, 0.2, None)
    stream = bp(nz(n), 500, 3000) * fast * np.minimum(t / 0.06, 1) * np.clip((d - t) / 0.4, 0, 1)
    b = stream * 0.25; k = 0.05
    while k < d - 0.3:
        f0 = j(400, 1200); dd = j(0.012, 0.03)
        place(b, np.sin(2 * np.pi * np.cumsum(expsweep(f0, f0 * 1.6, dd)) / SR) * expenv(N(dd), dd * 0.4, 0.0008), N(k), j(0.05, 0.15)); k += R().exponential(1 / 25)
    soak = lp(nz(n), 400) * np.clip((t - 0.2) / 0.5, 0, 1) * np.clip((d - t) / 0.4, 0, 1) * 0.15
    return b + soak
def dig():
    items = []; t = 0.0
    for i in range(2):
        cr = np.zeros(N(0.2))
        for _ in range(18): place(cr, g(0.012, 400, 2500, 0.004), N(j(0, 0.15)), j(0.3, 0.7))
        n = N(0.25); sw = lp(nz(n), 1500) * np.sin(np.pi * np.arange(n) / n) * 0.25
        items += [(t, cr, 0.8), (t + 0.05, sw, 1.0), (t + 0.32, thump(80, 140, 0.03), 0.5)]; t += 0.55
    return mix(t + 0.1, items)
def chop_wood():
    crack = g(0.05, 1000, 6000, 0.005)
    thock = tri(expsweep(230, 150, 0.12), 0.12, steps=False) * expenv(N(0.12), 0.03, 0.001) + 0.6 * bp(nz(N(0.12)), 300, 900) * expenv(N(0.12), 0.025, 0.001)
    split = np.zeros(N(0.3))
    for _ in range(10): place(split, g(0.01, 1500, 5000, 0.002), N(j(0, 0.25)), j(0.2, 0.5))
    return mix(0.65, [(0, crack, 0.8), (0, thock, 1.0), (0.05, split, 0.6), (0.06, rustle(0.25, 800, 3000), 0.3)])
def stone_clink():
    def clink(f):
        n = N(0.25); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.035) + 0.5 * np.sin(2 * np.pi * f * 1.63 * t) * np.exp(-t / 0.02)) + click(2000, 7000, 0.001, 0.25)
    return mix(0.5, [(0, clink(j(2600, 3000)), 0.8), (j(0.11, 0.15), clink(j(3200, 3700)), 0.5)])
def pick_berries():
    items = [(0, rustle(0.3, 800, 4000, 80), 0.6)]; t = 0.06
    for i in range(int(R().integers(2, 4))):
        pop = np.sin(2 * np.pi * np.cumsum(expsweep(j(650, 750), j(1150, 1300), 0.03)) / SR) * expenv(N(0.03), 0.012, 0.001)
        items.append((t, pop, 0.5)); t += j(0.12, 0.18)
    items += [(t + 0.05, thump(160, 260, 0.012), 0.4), (t + 0.05, rustle(0.08, 900, 3500), 0.3)]
    return mix(t + 0.25, items)

def build():
    F = []
    for v in (1, 2, 3):
        F += [(f'pickup_{v}', 5000 + v, pickup), (f'drop_{v}', 5010 + v, drop), (f'make_{v}', 5020 + v, make),
              (f'hammer_{v}', 5030 + v, (lambda v=v: hammer(double=(v == 3)))), (f'gather_{v}', 5040 + v, gather)]
    F += [('put_away', 5101, put_away), ('take_out', 5102, take_out), ('give', 5103, give), ('combine', 5104, combine),
          ('unmake', 5105, unmake), ('invent', 5106, invent), ('design', 5107, design), ('design_works', 5108, design_works),
          ('design_fails', 5109, design_fails), ('saw', 5110, saw), ('build_done', 5111, build_done), ('mend', 5112, mend),
          ('water_plants', 5113, water_plants), ('dig', 5114, dig), ('chop_wood', 5115, chop_wood),
          ('stone_clink', 5116, stone_clink), ('pick_berries', 5117, pick_berries)]
    return F

if __name__ == '__main__':
    only = set(sys.argv[1:])
    for name, sd, fn in build():
        if only and name not in only: continue
        seed(sd); x = level(trim_sfx(hp(fn(), 40), tail_keep=0.03, fade_out=0.02), -16.0)
        write(f'{OUT}/{name}', x)
        print(f'{name:16s} {len(x)/SR:5.2f}s {lufs(x):6.2f} LUFS {true_peak_db(x):6.2f} dBTP')
