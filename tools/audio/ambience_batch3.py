"""Batch 3: outdoor + weather ambience loops for 'the house'. Same framework as ambience_batch2
(periodic modulation curves, beds rendered L+2 s and equal-power crossfaded, circular events,
circular high-pass, zero-crossing start, -28 LUFS). Continuous textures (rain, stream, wind) are
treated as beds; sparse accents as wrapped events. Loop lengths differ from batch 2 and each other."""
import sys
from ambience_batch2 import *
from ambience_batch2 import bee, bird_phrase, cricket_field, creak
from scipy.signal import fftconvolve

def wind(L, M, lo, hi, base=0.6, depth=0.3, floor=0.3, kmax=8, slope=0.8, low=0.25):
    g = curve(L, M, kmax=kmax, slope=slope)
    gust = np.clip(base + depth * g, floor, None)
    fc = lo + (hi - lo) * np.clip((g + 1.8) / 3.8, 0, 1) ** 1.4
    y = lp_sweep(white(M), fc) * gust ** 1.5 + low * bp(white(M), 90, 350) * gust
    return y, g

def impulses(M, rate, amp_lo=0.2, amp_hi=1.0, mod=None):
    """Random impulse train (Poisson, mean `rate`/s, optionally scaled by a modulation curve)."""
    p = rate / SR * (np.ones(M) if mod is None else mod)
    x = np.zeros(M); idx = np.nonzero(R().random(M) < p)[0]
    x[idx] = R().uniform(amp_lo, amp_hi, len(idx)) ** 2
    return x

def drop_kernel(dur, tau):
    n = N(dur); return white(n) * np.exp(-np.arange(n) / SR / tau)

def chirp(f0, f1, d, tau):
    n = N(d); return np.sin(2 * np.pi * np.cumsum(expsweep(f0, f1, d)) / SR) * expenv(n, tau, 0.0008)

def frogs(L, specs):
    out = np.zeros(L); L_s = L / SR
    for base, gap in specs:
        for t in times(L_s, gap, 3.5, jitter=0.5):
            call = np.zeros(N(1.0)); tt = 0.0
            for _ in range(R().integers(1, 4)):
                d = R().uniform(0.12, 0.22); n = N(d); f = base * R().uniform(0.95, 1.05)
                am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * R().uniform(28, 40) * np.arange(n) / SR))
                x = pulse(expsweep(f * 1.08, f * 0.9, d), d, 0.25) * am * env_ar(n, 0.02, 0.06)
                place(call, lp(x, 2200), N(tt)); tt += d + R().uniform(0.08, 0.16)
            place(out, call, t, R().uniform(0.05, 0.09), wrap=True)
    return out

def crackles(L, rate, gain, big_p=0.08):
    """Fire crackle: clustered tiny pops + occasional bigger snaps."""
    out = np.zeros(L); L_s = L / SR
    for t in times(L_s, 1 / rate, 0.01, jitter=0.95):
        if R().random() < big_p:
            k = R().integers(2, 6); tt = 0.0; e = np.zeros(N(0.3))
            for _ in range(k):
                place(e, grain(0.02, 800, 6000, R().uniform(0.002, 0.006)), N(tt), R().uniform(0.5, 1.0)); tt += R().uniform(0.005, 0.04)
            place(out, e, t, gain * 2.2, wrap=True)
        else:
            lo = R().uniform(1500, 3500)
            place(out, grain(0.01, lo, min(lo * 3, 12000), R().uniform(0.0008, 0.002)), t, gain * R().uniform(0.2, 1.0), wrap=True)
    return out

def owl_call():
    """'hoo ... hoo-hoo-hooo': soft descending glides (no held pitch), breathy, low-passed."""
    f0 = R().uniform(370, 430); e = np.zeros(N(3.0)); tt = 0.0
    for d, gap, drop in [(0.32, 0.55, 160), (0.16, 0.10, 140), (0.16, 0.10, 140), (0.48, 0.0, 260)]:
        n = N(d); t = np.arange(n) / SR
        fr = f0 * 2 ** ((60 - drop * t / d) / 1200)
        x = np.sin(2 * np.pi * np.cumsum(fr) / SR) + 0.15 * np.sin(4 * np.pi * np.cumsum(fr) / SR)
        x = x * np.sin(np.pi * t / d) ** 1.5 + 0.08 * lp(white(n), 1200) * np.sin(np.pi * t / d)
        place(e, x, N(tt)); tt += d + gap
    return lp(delay(e, 0.13, fb=0.25, mix=0.3, damp=1200), 1500)

# ------------------------------------------------------------------ yard
def yard(night):
    L_s = 61; L = N(L_s); M = L + N(XF_S)
    seed(1000); w, g = wind(L, M, 350, 2600, base=0.62, depth=0.24, floor=0.42)
    leaves = hp(white(M), 1500) * np.clip(0.6 + 0.3 * g, 0.25, None) ** 2 * 0.25
    bed = xfade_loop(w + leaves, L); bed = bed / bed.std() * 0.02
    if night: bed = lp(bed, 2500) * 0.75
    ev = np.zeros(L)
    if not night:
        seed(1001)
        for t in times(L_s, 12.0, 6.0, jitter=0.5): place(ev, bird_phrase(), t, R().uniform(0.05, 0.09), wrap=True)
        seed(1002); Mf = L + N(XF_S); fl = np.clip(1 + 0.4 * curve(L, Mf, kmax=40), 0.3, None)
        roar = xfade_loop(lp(white(Mf), 500) * fl, L) * 0.006
        ev += roar + crackles(L, 14, 0.05)
    else:
        seed(1003); ev += cricket_field(L, [(4100, 0.52, 3, 0.018), (4800, 0.66, 3, 0.012)])
        seed(1004)
        for t in times(L_s, 18.0, 11.0, jitter=0.35): place(ev, owl_call(), t, R().uniform(0.02, 0.03), wrap=True)
        seed(1005); Mf = L + N(XF_S); fl = np.clip(1 + 0.3 * curve(L, Mf, kmax=20), 0.4, None)
        glow = xfade_loop(lp(white(Mf), 300) * fl, L) * 0.004
        ev += glow + crackles(L, 3, 0.03, big_p=0.03)
    return finish('yard_night' if night else 'yard', bed + ev)

# ------------------------------------------------------------------ meadow
def stream(L, M):
    """Babbling stream: turbulent band noise with fast random level + dense tiny bubble chirps."""
    fast = np.clip(1 + 0.35 * curve(L, M, kmax=300, slope=0.3), 0.2, None)
    y = (bp(white(M), 300, 2500) * 0.7 + bp(white(M), 2500, 6000) * 0.15) * fast
    bub = np.zeros(M); t = 0.0
    while t < M / SR - 0.05:
        f0 = R().uniform(300, 1400); d = R().uniform(0.01, 0.035)
        place(bub, chirp(f0, f0 * R().uniform(1.3, 2.2), d, d * 0.5), N(t), R().uniform(0.1, 0.5))
        t += R().exponential(1 / 35)
    return y * 0.03 + bub * 0.05

def meadow(night):
    L_s = 65; L = N(L_s); M = L + N(XF_S)
    seed(1100); gw, g = wind(L, M, 600, 4500, base=0.55, depth=0.3, floor=0.25, low=0.1)
    grass = hp(gw, 400)
    seed(1101); st = stream(L, M)
    if not night:
        bed = xfade_loop(grass / grass.std() * 0.02 + st, L)
        seed(1102); ev = np.zeros(L)
        for t in times(L_s, 6.0, 2.0, jitter=0.8):        # grasshopper rasps: jittered pulse trains of noise
            d = R().uniform(0.5, 1.8); rate = R().uniform(10, 18); e = np.zeros(N(d + 0.05)); x = 0.0
            while x < d:
                place(e, grain(0.025, 5000, 8500, 0.008), N(x), np.sin(np.pi * x / d) * R().uniform(0.6, 1.0))
                x += (1 / rate) * R().uniform(0.8, 1.2)
            place(ev, lp(e, 7500), t, R().uniform(0.03, 0.06), wrap=True)
        for t in times(L_s, 14.0, 6.0, jitter=0.6):
            place(ev, bee(R().uniform(1.5, 2.8)), t, R().uniform(0.03, 0.05), wrap=True)
    else:
        bed = xfade_loop(grass / grass.std() * 0.006 + st, L)
        seed(1103); ev = frogs(L, [(290, 6.5), (480, 9.0)]) * 0.55
        seed(1104); ev += cricket_field(L, [(3800, 0.5, 3, 0.016), (4400, 0.6, 3, 0.012), (5100, 0.78, 4, 0.009)])
    return finish('meadow_night' if night else 'meadow', bed + ev)

# ------------------------------------------------------------------ weather
def rain_roof():
    L_s = 57; L = N(L_s); M = L + N(XF_S)
    seed(1200); inten = np.clip(1 + 0.2 * curve(L, M, kmax=4), 0.5, None)
    roof = fftconvolve(impulses(M, 900, mod=inten), drop_kernel(0.02, 0.004), mode='same')
    roof = lp(bp(roof, 150, 3000), 1400)                                   # muffled through the roof
    roar = lp(white(M), 500) * inten * 0.35
    win = fftconvolve(impulses(M, 5, 0.3, 1.0, mod=inten), drop_kernel(0.012, 0.0015), mode='same')
    win = bp(win, 1800, 6500)                                             # sharper ticks on the window
    bed = xfade_loop(roof / roof.std() * 0.016 + roar / roar.std() * 0.01 + win * 0.35, L)
    seed(1201); ev = np.zeros(L)
    for f0, gap in [(950, 1.9), (1250, 3.1)]:                             # two gutter drips, own cadence
        for t in times(L_s, gap, gap * 0.6, jitter=0.25):
            f = f0 * R().uniform(0.97, 1.03)
            place(ev, lp(chirp(f, f * 1.6, 0.05, 0.012), 3000), t, R().uniform(0.03, 0.05), wrap=True)
    return finish('rain_roof', bed + ev)

def rain_ground():
    L_s = 53; L = N(L_s); M = L + N(XF_S)
    seed(1300); inten = np.clip(1 + 0.18 * curve(L, M, kmax=4), 0.5, None)
    hiss = bp(white(M), 600, 9000) * inten
    grass = bp(fftconvolve(impulses(M, 1400, mod=inten), drop_kernel(0.012, 0.002), mode='same'), 1200, 8000)
    splat = lp(fftconvolve(impulses(M, 40, 0.3, 1.0, mod=inten), drop_kernel(0.04, 0.01), mode='same'), 2500)
    pud = np.zeros(M); t = 0.0
    while t < M / SR - 0.05:                                              # puddle plinks
        f0 = R().uniform(800, 2400); d = R().uniform(0.015, 0.04)
        place(pud, chirp(f0, f0 * R().uniform(1.2, 1.8), d, d * 0.4), N(t), R().uniform(0.2, 1.0))
        t += R().exponential(1 / 5)
    bed = hiss / hiss.std() * 0.012 + grass / grass.std() * 0.01 + splat / splat.std() * 0.004 + pud * 0.02
    return finish('rain_ground', xfade_loop(bed, L))

def wind_strong():
    L_s = 79; L = N(L_s); M = L + N(XF_S)
    seed(1400); w, g = wind(L, M, 250, 3200, base=0.58, depth=0.36, floor=0.36, kmax=14, slope=0.6, low=0.35)
    hi = bp(white(M), 1500, 5000) * np.clip(g, 0, None) ** 2 * 0.25        # extra hiss on strong gusts
    bed = xfade_loop(w + hi, L); bed = bed / bed.std() * 0.02
    seed(1401); ev = np.zeros(L); gl = g[:L]
    pk = signal.argrelmax(gl[::441], order=400)[0] * 441
    for i, p in enumerate([p for p in pk if gl[p] > 0.5][:8]):         # gust whistles: monotonic glides only
        d = R().uniform(1.2, 2.0); n = N(d); s = R().uniform(9, 12) * (1 if i % 2 == 0 else -1)
        f0 = R().uniform(650, 900); fr = f0 * 2 ** (s / 12 * np.linspace(0, 1, n)) * (1 + 0.003 * curve(n, n, kmax=20))
        x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * (1 + 0.3 * curve(n, n, kmax=25)) * np.sin(np.pi * np.arange(n) / n) ** 2
        place(ev, x, p / SR - d / 2, 0.02 * min(1.3, gl[p]), wrap=True)
    return finish('wind_strong', bed + ev)

def snow():
    """Muffled near-silence: soft low-passed hush with very slow breathing, occasional snow slumps."""
    L_s = 83; L = N(L_s); M = L + N(XF_S)
    seed(1500); br = np.clip(1 + 0.12 * curve(L, M, kmax=3), 0.6, None)
    hush = (lp(white(M), 700, 2) + 0.08 * bp(white(M), 1500, 4000)) * br
    bed = xfade_loop(hush, L); bed = bed / bed.std() * 0.02
    seed(1501); ev = np.zeros(L)
    for t in times(L_s, 21.0, 12.0, jitter=0.4):                         # snow sliding off a branch
        d = R().uniform(0.5, 1.0); n = N(d)
        place(ev, lp(white(n), 900) * env_ar(n, 0.05, d * 0.7), t, R().uniform(0.012, 0.02), wrap=True)
    return finish('snow', bed + ev)

def heat():
    """Summer cicadas: jittered tymbal-click trains of band noise (no fixed pulse rate -> no
    spectral lines), each cicada swelling and fading in waves; warm low-pass at 4.5 kHz."""
    L_s = 74; L = N(L_s); M = L + N(XF_S)
    seed(1600); bed = lp(white(M), 900) * (1 + 0.1 * curve(L, M, kmax=4))
    bed = xfade_loop(bed, L); bed = bed / bed.std() * 0.01
    seed(1601); ev = np.zeros(L)
    voices = [(2900, 0.06, 9.0), (3400, 0.05, 11.0), (2500, 0.045, 13.0), (3800, 0.035, 15.0)]
    for fc, gain, gap in voices:
        for t in times(L_s, gap, gap * 0.6, jitter=0.4):
            d = R().uniform(4.0, 7.0); n = N(d); rate = R().uniform(140, 220)
            clicks = np.zeros(n); x = 0.0
            while x < d:
                i = int(x * SR)
                if i < n: clicks[i] = R().uniform(0.5, 1.0)
                x += (1 / rate) * R().uniform(0.6, 1.4)
            body = fftconvolve(clicks, drop_kernel(0.006, 0.0012), mode='same')
            body = bp(body, fc * 0.75, fc * 1.3)
            tt = np.arange(n) / d
            wave_env = np.clip(np.sin(np.pi * tt ** 0.7), 0, None) ** 1.5                 # swell, then fade
            pulse_env = 1 - 0.35 * (0.5 + 0.5 * np.sin(2 * np.pi * R().uniform(3, 7) * tt * d))  # gentle pulsing
            place(ev, body * wave_env * pulse_env, t, gain, wrap=True)
    ev = lp(ev, 4000, 4)                     # warm: 4th-order low-pass, nothing piercing above ~5 kHz
    return finish('heat', bed + ev / (np.std(ev) + 1e-12) * 0.02)

ROOMS = {'yard': lambda: yard(False), 'yard_night': lambda: yard(True),
         'meadow': lambda: meadow(False), 'meadow_night': lambda: meadow(True),
         'rain_roof': rain_roof, 'rain_ground': rain_ground, 'wind_strong': wind_strong, 'snow': snow, 'heat': heat}
if __name__ == '__main__':
    for k in (sys.argv[1:] or ROOMS): ROOMS[k]()
