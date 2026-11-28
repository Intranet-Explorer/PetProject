"""Batch 4: a hob's body and voice (sfx). All procedural; voice sounds use hob_voice (same timbre).
Each file: render -> 40 Hz high-pass -> trim lead/trail + short fade -> -16 LUFS integrated, <= -1 dBTP.
Very short files (< 0.4 s, e.g. footsteps) are measured by zero-padding to one 400 ms BS.1770 block
(silence is below the absolute gate's influence only via the block energy), i.e. loudness = energy
averaged over 400 ms. This is stricter than a momentary reading of the click itself."""
import sys
from hob_voice import *
OUT = '/workspace/house-audio/sfx'; os.makedirs(OUT, exist_ok=True)

def nz(n): return R().normal(0, 1, n)
def g(dur, lo, hi, tau, a=0.0005):
    n = N(dur); return bp(nz(n), lo, hi) * expenv(n, tau, a)

# ------------------------------------------------------------------ footsteps
def step(surface):
    """Tiny soft footstep: a short contact + a soft scuff tail (keeps the crest factor low enough
    that -16 LUFS fits under -1 dBTP without crushing the transient)."""
    j = lambda a, b: R().uniform(a, b)
    def scuff(d, lo, hi, a=0.25):
        n = N(d); return bp(nz(n), lo, hi) * np.minimum(np.arange(n) / N(0.01), 1) * np.exp(-np.arange(n) / SR / (d / 3)) * a
    if surface == 'wood':
        b = np.zeros(N(0.24))
        place(b, tri(expsweep(j(240, 290), j(130, 160), 0.07), 0.07, steps=False) * expenv(N(0.07), j(0.018, 0.026), 0.0015), 0, 0.7)
        place(b, g(0.04, 500, 2600, j(0.004, 0.007)), 0, 0.35)
        place(b, lp(nz(N(0.12)), 1100) * expenv(N(0.12), 0.035, 0.002), 0, 0.3)
        place(b, scuff(0.16, 600, 2500, 0.12), j(0.01, 0.03))
    elif surface == 'stone':
        b = np.zeros(N(0.24))
        place(b, g(0.03, 2000, 6500, j(0.002, 0.003)), 0, 0.4)
        place(b, g(0.06, 700, 2000, j(0.012, 0.018), 0.001), 0, 0.55)
        place(b, scuff(0.18, 1500, 5000, 0.16), j(0.01, 0.03))
    elif surface == 'grass':
        n = N(0.24); b = lp(hp(nz(n), 1800), 8000) * adsr(n, 0.012, 0.06, 0.45, 0.1, N(0.12)) * 0.35
        for _ in range(R().integers(6, 12)):
            place(b, g(0.01, 2000, 6500, j(0.001, 0.003)), j(0.0, 0.1), j(0.2, 0.45))
    else:   # dirt
        b = np.zeros(N(0.24))
        place(b, lp(nz(N(0.1)), 350) * expenv(N(0.1), 0.03, 0.002), 0, 0.6)
        for _ in range(R().integers(12, 20)):
            place(b, g(0.012, 400, 2500, j(0.002, 0.005)), j(0.0, 0.11), j(0.25, 0.55))
        place(b, scuff(0.18, 400, 2200, 0.2), j(0.0, 0.02))
    return b

# ------------------------------------------------------------------ body
def thump(lo=110, hi=190, tau=0.025):
    return tri(expsweep(hi, lo, 0.09), 0.09, steps=False) * expenv(N(0.09), tau, 0.002) + 0.5 * lp(nz(N(0.09)), 450) * expenv(N(0.09), 0.02, 0.002)

def rustle(dur, lo=600, hi=3500, dens=60):
    n = N(dur); b = bp(nz(n), lo, hi) * np.sin(np.pi * np.arange(n) / n) ** 1.5 * 0.25
    t = 0.0
    while t < dur - 0.02:
        place(b, g(0.012, lo * 2, hi * 1.6, 0.003), t, R().uniform(0.1, 0.4) * np.sin(np.pi * t / dur)); t += R().exponential(1 / dens)
    return b

def hop():
    b = np.zeros(N(0.42))
    place(b, tri(expsweep(330, 900, 0.08), 0.08) * adsr(N(0.08), 0.004, 0.03, 0.7, 0.02, N(0.06)), 0, 0.35)   # retro hop blip
    place(b, rustle(0.08, 900, 4000), 0, 0.6)
    place(b, thump(130, 220, 0.02), 0.24, 0.8); place(b, rustle(0.1, 800, 3500), 0.24, 0.4)
    return b

def sit():
    b = np.zeros(N(0.45)); place(b, rustle(0.22), 0, 0.8); place(b, thump(100, 170, 0.03), 0.14, 0.9); return b

def lie_down():
    b = np.zeros(N(1.3)); place(b, rustle(0.45, 500, 3000), 0, 0.8)
    place(b, thump(90, 150, 0.035), 0.3, 0.8); place(b, thump(110, 170, 0.02), 0.52, 0.35)
    place(b, rustle(0.25, 500, 2500), 0.5, 0.4)
    place(b, breath_noise(0.55, 300, 1600, 'exh', 'o'), 0.68, 0.5)
    return b

def yawn():
    d = 1.3; n = N(d); t = np.linspace(0, d, n)
    st = np.interp(t, [0, 0.35, 1.1, d], [2, 6, -4, -5])            # rise then a long fall: never held
    y = voiced(st * 100, [(0, 'e'), (0.25, 'a'), (0.6, 'a'), (0.85, 'o'), (0.95, 'u'), (1, 'm')], breath=0.3)
    y *= adsr(n, 0.08, 0.3, 0.8, 0.25, n - N(0.25))
    return y + 0.4 * breath_noise(d, 400, 2500, 'sin', 'a')

def sleep_breath():
    b = np.zeros(N(1.95)); place(b, breath_noise(0.8, 400, 2400, 'sin', 'o'), 0, 0.8)
    ex = breath_noise(1.0, 200, 1400, 'exh', 'u')
    purr = voiced(np.linspace(-700, -1100, N(0.6)), [(0, 'u')], breath=0.5) * adsr(N(0.6), 0.1, 0.2, 0.7, 0.25, N(0.35))
    place(b, ex, 0.9, 0.9); place(b, purr, 0.95, 0.08)
    return b

def stretch():
    b = np.zeros(N(1.05)); place(b, rustle(0.75, 500, 3000, 80), 0, 0.7)
    n1 = N(0.32); c1 = np.linspace(0, 450, n1) + 40 * np.sin(2 * np.pi * 9 * np.arange(n1) / SR)
    v1 = voiced(c1, [(0, 'm'), (1, 'm')], breath=0.15) * adsr(n1, 0.04, 0.1, 0.8, 0.05, n1 - N(0.05))
    n2 = N(0.28); v2 = voiced(np.linspace(450, -150, n2), [(0, 'a'), (1, 'o')], breath=0.15) * adsr(n2, 0.01, 0.1, 0.8, 0.1, n2 - N(0.1))
    place(b, v1, 0.12, 0.5); place(b, v2, 0.45, 0.55)
    return b

def groom():
    b = np.zeros(N(1.55)); t = 0.0
    for i in range(int(R().integers(5, 7))):
        d = R().uniform(0.08, 0.13); n = N(d)
        lick = bp(nz(n), 1500, 5000) * np.sin(np.pi * np.arange(n) / n) ** 2
        place(b, lick, t, R().uniform(0.25, 0.4))
        smack = g(0.015, 500, 2000, 0.003) + 0.3 * np.sin(2 * np.pi * np.cumsum(expsweep(650, 300, 0.015)) / SR) * expenv(N(0.015), 0.005)
        place(b, smack, t + d, 0.3)
        t += d + R().uniform(0.12, 0.2)
    place(b, rustle(1.4, 700, 3500, 30), 0.0, 0.25)
    return b

def eat(kind):
    b = np.zeros(N(1.4)); t = 0.0
    lo, hi = {1: (1200, 5500), 2: (700, 3000), 3: (900, 4500)}[kind]
    for i in range(int(R().integers(3, 6))):
        for _ in range(int(R().integers(12, 25))):
            place(b, g(0.01, lo, hi, R().uniform(0.0015, 0.004)), t + R().uniform(0, 0.06), R().uniform(0.2, 0.6))
        place(b, lp(nz(N(0.05)), 260) * expenv(N(0.05), 0.015, 0.002), t, 0.5)
        if kind != 1 and R().random() < 0.5: place(b, g(0.02, 400, 1500, 0.006), t + 0.08, 0.25)   # softer, wetter
        t += R().uniform(0.2, 0.28)
    return b[:N(t + 0.1)]

def drink():
    b = np.zeros(N(1.4)); t = 0.0
    for i in range(5):
        place(b, g(0.015, 2000, 5000, 0.004), t, 0.3)
        f = R().uniform(420, 520)
        place(b, np.sin(2 * np.pi * np.cumsum(expsweep(f, f * 2.3, 0.025)) / SR) * expenv(N(0.025), 0.01, 0.001), t + 0.01, 0.35)
        place(b, g(0.04, 1000, 4000, 0.015), t + 0.015, 0.25)
        t += R().uniform(0.2, 0.25)
    return b[:N(t + 0.1)]

# ------------------------------------------------------------------ voice reactions
def cat(*parts, gap=0.03):
    out = []
    for p in parts: out += [p, np.zeros(N(gap))]
    return np.concatenate(out)

def voice_happy():
    a = syl(0.11, 1.0, 'u', 'rise', 2.0, 'none', 0.9, vowel2='i')
    b = syl(0.17, 4.0, 'i', 'arch', 3.5, 'noise', 1.0)
    return cat(a, b, gap=0.035)

def voice_sad():
    n = N(0.55); c = np.linspace(-150, -650, n) + 35 * np.sin(2 * np.pi * 5 * np.arange(n) / SR)
    a = voiced(c, [(0, 'o'), (1, 'u')], breath=0.15) * adsr(n, 0.03, 0.2, 0.75, 0.15, n - N(0.15))
    m = voiced(np.linspace(-650, -900, N(0.2)), [(0, 'm')], breath=0.1) * adsr(N(0.2), 0.02, 0.05, 0.7, 0.08, N(0.12))
    return cat(a, m * 0.7, gap=0.04)

def rough(y, rate=34, depth=0.45):
    n = len(y); t = np.cumsum(R().uniform(0.7, 1.3, n) * rate / SR)
    return y * (1 - depth * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * t))))

def voice_angry():
    a = rough(syl(0.12, -4.0, 'm', 'fall', 1.5, 'nasal', 1.0, breath=0.12))
    p = bp(nz(N(0.02)), 1500, 5000) * np.hanning(N(0.02)) * 0.3
    b = rough(syl(0.2, -3.0, 'a', 'fall', 4.0, 'none', 1.1, breath=0.12))
    return cat(a, p, b, gap=0.02)

def voice_scared():
    def eep(off):
        n = N(0.15); c = off * 100 + np.linspace(0, 250, n) + 80 * np.sin(2 * np.pi * 11 * np.arange(n) / SR)
        return voiced(c, [(0, 'i')], breath=0.12) * adsr(n, 0.006, 0.05, 0.8, 0.03, n - N(0.03))
    return cat(breath_noise(0.07, 1000, 4000, 'sin', 'i') * 0.4, eep(5.5), eep(7.5), gap=0.04)

def voice_curious():
    n = N(0.24); m = voiced(np.linspace(-100, 250, n), [(0, 'm')], breath=0.08) * adsr(n, 0.02, 0.1, 0.8, 0.03, n - N(0.03))
    q = syl(0.16, 3.0, 'u', 'rise', 4.5, 'none', 1.0, vowel2='e')
    return cat(m, q, gap=0.01)

def voice_surprised():
    gs = breath_noise(0.08, 900, 3500, 'sin', 'a') * 0.5
    n = N(0.28); t = np.arange(n) / SR
    c = 200 + 600 * (1 - np.exp(-t / 0.02)) - 500 * np.clip((t - 0.06) / 0.22, 0, 1)
    o = voiced(c, [(0, 'a'), (0.3, 'o'), (1, 'o')], breath=0.1) * adsr(n, 0.005, 0.1, 0.8, 0.08, n - N(0.08))
    return cat(gs, o * 1.2, gap=0.0)

def laugh():
    parts = []
    for i in range(int(R().integers(4, 6))):
        h = breath_noise(0.03, 900, 3500, 'sin', 'e') * 0.35
        parts += [h, syl(R().uniform(0.07, 0.09), 4 - 1.6 * i, R().choice(['e', 'a']), 'fall', 1.5, 'none', 1.0 - 0.08 * i, breath=0.15)]
    return cat(*parts, gap=0.035)

def cry():
    def wail(d, c0, c1, v1, v2):
        n = N(d); t = np.arange(n) / SR
        c = np.linspace(c0, c1, n) + 120 * np.sin(2 * np.pi * 6 * t)
        return voiced(c, [(0, v1), (1, v2)], breath=0.2) * adsr(n, 0.02, 0.1, 0.8, 0.1, n - N(0.1))
    sob = lambda: syl(0.07, 2.0, 'a', 'fall', 2.0, 'none', 0.7, breath=0.25)
    sniff = breath_noise(0.12, 1500, 5000, 'sin') * 0.25
    return cat(wail(0.32, 300, -100, 'u', 'a'), sob(), sob(), wail(0.45, 200, -500, 'a', 'o'), sniff, gap=0.04)

def gasp():
    inh = breath_noise(0.25, 700, 3500, 'sin', 'a')
    n = N(0.07); v = voiced(np.linspace(300, 700, n), [(0, 'a')], breath=0.2) * adsr(n, 0.004, 0.02, 0.7, 0.02, n - N(0.02))
    b = np.zeros(N(0.42)); place(b, inh, 0, 0.7); place(b, v, 0.2, 0.6); return b

def sigh():
    b = np.zeros(N(1.45)); place(b, breath_noise(0.3, 600, 2500, 'sin', 'e'), 0, 0.35)
    ex = breath_noise(1.0, 300, 2500, 'exh', 'a')
    n = N(0.8); v = voiced(np.linspace(-100, -600, n), [(0, 'a'), (1, 'o')], breath=0.4) * adsr(n, 0.06, 0.2, 0.6, 0.3, n - N(0.3))
    place(b, ex, 0.35, 0.8); place(b, v, 0.38, 0.35); return b

def hum(notes):
    """Hummed tune: closed-mouth 'm' voice, legato, each note <= 0.22 s with a re-articulation dip."""
    base = fq('C5'); total = sum(d for _, d in notes); n = N(total + 0.1)
    cents = np.zeros(n); amp = np.ones(n); t = 0.0; prev = None
    for name, d in notes:
        i0, i1 = N(t), N(t + d); c = 1200 * np.log2(fq(name) / base)
        seg = np.full(i1 - i0, c)
        if prev is not None:
            k = min(N(0.025), len(seg)); seg[:k] = np.linspace(prev, c, k)       # 25 ms portamento
        cents[i0:i1] = seg; dip = min(N(0.04), i1 - i0); amp[i0:i0 + dip] *= np.linspace(0.55, 1, dip)
        prev = c; t += d
    cents[N(total):] = prev
    y = voiced(cents, [(0, 'm')], breath=0.07, base=base) * amp
    return y * adsr(n, 0.03, 0.1, 0.9, 0.15, N(total))

TUNES = {1: [('E5', .21), ('G5', .07), ('A5', .14), ('G5', .14), ('E5', .21), ('D5', .14), ('C5', .22)],      # house_day motif
         2: [('E5', .2), ('G5', .1), ('A5', .1), ('G5', .2), ('E5', .22), ('D5', .12), ('C5', .1), ('D5', .22)],  # house_night lullaby
         3: [('C5', .14), ('F5', .14), ('G5', .14), ('A5', .14), ('Bb5', .21), ('A5', .07), ('G5', .22), ('F5', .2)]}  # outdoors_day

def build():
    files = []
    for s_i, surf in enumerate(['wood', 'stone', 'grass', 'dirt']):
        for v in (1, 2, 3):
            files.append((f'step_{surf}_{v}', 4000 + 10 * s_i + v, lambda surf=surf: step(surf)))
    files += [('hop', 4101, hop), ('sit', 4102, sit), ('lie_down', 4103, lie_down), ('yawn', 4104, yawn),
              ('sleep_breath', 4105, sleep_breath), ('stretch', 4106, stretch), ('groom', 4107, groom),
              ('eat_1', 4111, lambda: eat(1)), ('eat_2', 4112, lambda: eat(2)), ('eat_3', 4113, lambda: eat(3)),
              ('drink', 4114, drink)]
    modes = ['statement', 'question', 'statement', 'exclaim', 'question', 'statement', 'exclaim', 'statement']
    for v in range(1, 9):
        files.append((f'voice_babble_{v}', 4200 + v, lambda v=v: babble(4200 + v, modes[v - 1], max_s=1.8)))
    files += [('voice_happy', 4301, voice_happy), ('voice_sad', 4302, voice_sad), ('voice_angry', 4303, voice_angry),
              ('voice_scared', 4304, voice_scared), ('voice_curious', 4305, voice_curious), ('voice_surprised', 4306, voice_surprised),
              ('laugh', 4311, laugh), ('cry', 4312, cry), ('gasp', 4313, gasp), ('sigh', 4314, sigh)]
    for v in (1, 2, 3): files.append((f'hum_tune_{v}', 4400 + v, lambda v=v: hum(TUNES[v])))
    return files

if __name__ == '__main__':
    only = set(sys.argv[1:])
    for name, sd, fn in build():
        if only and name not in only: continue
        seed(sd); x = level(trim_sfx(hp(fn(), 40), tail_keep=0.03, fade_out=0.02), -16.0)
        write(f'{OUT}/{name}', x)
        print(f'{name:24s} {len(x)/SR:5.2f}s {lufs(x):6.2f} LUFS {true_peak_db(x):6.2f} dBTP')
