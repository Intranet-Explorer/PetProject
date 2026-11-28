"""Batch 2: room ambience loops for 'the house'. All procedural (noise + soft retro tonal accents).
Every room: bed (filtered noise with periodic modulation curves, rendered L+2 s and equal-power
crossfaded at the seam) + sparse seeded events placed circularly (wrapping across the seam);
echoes are computed circularly; circular 30 Hz high-pass; start on a zero crossing with an exact-zero
32-sample taper; leveled to -28 LUFS integrated, <= -1 dBTP.
Day/night pairs share loop length, bed seed and day-event seed; night adds/swaps layers."""
import sys
import synth as S
from synth import *
OUT = '/workspace/house-audio/ambience'; os.makedirs(OUT, exist_ok=True)
TARGET = -28.0; XF_S = 2.0

def seed(s): S.rng = np.random.default_rng(s)
def R(): return S.rng

# ------------------------------------------------------------------ framework
def curve(L, M=None, kmax=6, slope=1.0, rate=50):
    """Smooth zero-mean unit-std curve, exactly periodic over L samples, evaluated for M samples."""
    M = L if M is None else M; n = max(16, int(L / SR * rate)); t = np.arange(n) / n
    c = np.zeros(n)
    for k in range(1, kmax + 1):
        c += R().normal() / k ** slope * np.sin(2 * np.pi * k * t + R().uniform(0, 2 * np.pi))
    c = (c - c.mean()) / (c.std() + 1e-9)
    xs = (np.arange(M) % L) / L * n
    return np.interp(xs, np.arange(n + 1), np.append(c, c[0]))

def xfade_loop(y, L):
    XF = len(y) - L; r = np.linspace(0, np.pi / 2, XF)
    out = y[:L].copy(); out[:XF] = y[:XF] * np.sin(r) + y[L:L + XF] * np.cos(r)
    return out

def white(M): return R().choice([-1.0, 1.0], M) * 0.7 + R().normal(0, 0.3, M)

def circ(fn, x):
    L = len(x); return fn(np.concatenate([x, x, x]))[L:2 * L]

def times(L_s, mean_gap, min_gap, jitter=0.6, start=None):
    """Random event times on a circle of length L_s with a minimum spacing (also across the seam)."""
    t = R().uniform(0, mean_gap) if start is None else start; out = []
    while t < L_s:
        out.append(t); t += max(min_gap, mean_gap * (1 + R().uniform(-jitter, jitter)))
    if len(out) > 1 and (L_s - out[-1] + out[0]) < min_gap: out.pop()
    return out

def even_times(L_s, n, jitter=0.0):
    """n events evenly spaced around the loop (optionally jittered by a fraction of the spacing)."""
    p = L_s / n; return [(i * p + R().uniform(-jitter, jitter) * p) % L_s for i in range(n)]

def finish(name, mix):
    mix = circ(lambda z: hp(z, 30), mix)
    mix, _ = loop_finalize(mix, near=0)
    mix = level(mix, TARGET)
    write(f'{OUT}/{name}', mix)
    print(f'{name:20s} {len(mix)/SR:5.1f}s {lufs(mix):6.2f} LUFS {true_peak_db(mix):6.2f} dBTP', flush=True)
    return mix

def env_ar(n, a, r):
    e = np.ones(n); A, Rr = min(N(a), n), min(N(r), n)
    if A: e[:A] = np.linspace(0, 1, A) ** 2
    if Rr: e[-Rr:] *= np.linspace(1, 0, Rr) ** 2
    return e

def grain(dur, lo, hi, tau, a=0.0005):
    n = N(dur); return bp(white(n), lo, hi) * expenv(n, tau, a)

# ------------------------------------------------------------------ shared sound makers
def creak(dur, r0, r1, res, jit=0.18):
    """Stick-slip creak: jittered impulse train whose rate glides r0->r1 (wobbling), through resonances."""
    n = N(dur); x = np.zeros(n); t = 0.0
    wob = curve(n, n, kmax=3) * 0.15
    while t < dur:
        i = int(t * SR)
        if i >= n: break
        x[i] += R().uniform(0.5, 1.0)
        rate = r0 * (r1 / r0) ** (t / dur) * (1 + wob[i])
        t += (1 / rate) * (1 + R().uniform(-jit, jit))
    y = sum(g * bp(x, lo, hi) for lo, hi, g in res) + 0.15 * bp(white(n), res[0][0], res[0][1])
    y = y * env_ar(n, dur * 0.25, dur * 0.4)
    return y / (np.max(np.abs(y)) + 1e-12)          # unit peak; caller sets level

def cricket_field(L, specs):
    """specs: list of (carrier Hz, chirp period s, pulses, gain). Pulsed chirps with occasional rests."""
    out = np.zeros(L); L_s = L / SR
    for car, per, npulse, g in specs:
        t = R().uniform(0, per)
        while t < L_s:
            if R().random() < 0.04:            # the cricket pauses now and then
                t += R().uniform(2.0, 6.0); continue
            ch = np.zeros(N(npulse * 0.022 + 0.02)); c = car * (1 + R().uniform(-0.004, 0.004))
            for k in range(npulse):
                pn = N(0.013); tt = np.arange(pn) / SR
                p = (np.sin(2 * np.pi * c * tt) + 0.15 * np.sin(4 * np.pi * c * tt)) * np.hanning(pn)
                place(ch, p, N(k * 0.021))
            place(out, ch, N(t), g * R().uniform(0.8, 1.0), wrap=True)
            t += per * (1 + R().uniform(-0.06, 0.06))
    return lp(out, 7000)

def room_tone(M, L, lo=600, hiss=0.06):
    a = 1 + 0.08 * curve(L, M, kmax=3)
    return (lp(white(M), lo, 2) + hiss * hp(lp(white(M), 7000), 2500)) * a

# ------------------------------------------------------------------ rooms
def storeroom(night):
    L_s = 62; L = N(L_s); M = L + N(XF_S)
    seed(100); bed = lp(white(M), 260, 2) + 0.12 * lp(white(M), 900, 2)
    bed = xfade_loop(bed * (1 + 0.15 * curve(L, M, kmax=4)), L); bed = bed / bed.std() * 0.02
    seed(101); ev = np.zeros(L)
    for t in times(L_s, 8.5, 4.0):
        e = np.zeros(N(1.2)); big = R().random() < 0.55
        if big:
            th = tri(expsweep(R().uniform(95, 125), 50, 0.2), 0.2, steps=False) * expenv(N(0.2), 0.05, 0.002)
            place(e, th * 0.8 + lp(white(N(0.2)), 400) * expenv(N(0.2), 0.05, 0.002) * 0.6, 0)
        tt = 0.05 if big else 0.0
        for _ in range(R().integers(3, 10)):
            place(e, grain(R().uniform(0.01, 0.04), 300, 2500, R().uniform(0.004, 0.012)), N(tt), R().uniform(0.2, 0.5))
            tt += R().uniform(0.02, 0.09)
        place(ev, lp(e, 1800), t, R().uniform(0.18, 0.32) * (1.0 if big else 0.7), wrap=True)
    if night:
        seed(102)
        for t in times(L_s, 14.0, 7.0):
            e = np.zeros(N(3.0)); tt = 0.0
            for b in range(R().integers(1, 4)):
                bd = R().uniform(0.35, 1.2); rate = R().uniform(25, 45); x = 0.0
                while x < bd:
                    amp = np.sin(np.pi * x / bd) ** 0.7 * R().uniform(0.4, 1.0)
                    place(e, grain(R().uniform(0.004, 0.012), 2500, 7500, R().uniform(0.002, 0.004)), N(tt + x), amp)
                    x += (1 / rate) * R().uniform(0.6, 1.4)
                tt += bd + R().uniform(0.3, 0.8)
            if R().random() < 0.25:     # tiny squeak: fast glide, 70 ms
                sq = np.sin(2 * np.pi * np.cumsum(np.interp(np.arange(N(0.07)), [0, N(0.03), N(0.07)], [3400, 4300, 3600])) / SR)
                place(e, sq * np.hanning(N(0.07)), N(tt), 0.08)
            place(ev, lp(e, 6000), t, R().uniform(0.035, 0.06), wrap=True)
    return finish('storeroom_night' if night else 'storeroom', bed + ev)

def bell(f, gain=1.0):
    """Wind-chime bar: inharmonic partials, all freely decaying (fundamental tau 0.28 s)."""
    d = 2.2; n = N(d); t = np.arange(n) / SR
    parts = [(1.0, 1.0, 0.28), (2.76, 0.32, 0.16), (5.40, 0.14, 0.08), (8.93, 0.06, 0.05)]
    y = tri(f, d, steps=False) * 0.0
    for ratio, a, tau in parts:
        y += a * np.sin(2 * np.pi * f * ratio * t + R().uniform(0, 6.28)) * np.exp(-t / tau)
    y += 0.3 * hp(white(n), 3000) * np.exp(-t / 0.004)
    return y * np.minimum(t / 0.0015, 1) * gain

def music_room():
    L_s = 67; L = N(L_s); M = L + N(XF_S)
    seed(200); bed = xfade_loop(room_tone(M, L, 700, 0.08), L); bed = bed / bed.std() * 0.02
    seed(201); ev = np.zeros(L)
    notes = ['E5', 'G5', 'A5', 'C6', 'D6', 'E6', 'G6']
    for t in times(L_s, 16.0, 9.0, jitter=0.5):
        k = R().integers(3, 7); picks = R().permutation(len(notes))[:k]   # no bar struck twice per gust
        tt = 0.0; e = np.zeros(N(5.0))
        for p in picks:
            place(e, bell(fq(notes[p]), R().uniform(0.5, 1.0)), N(tt)); tt += R().uniform(0.12, 0.45)
        place(ev, lp(e, 7000), t, 0.07, wrap=True)
    return finish('music_room', bed + ev)

def cellar():
    L_s = 71; L = N(L_s); M = L + N(XF_S)
    seed(300); g = curve(L, M, kmax=8)
    bed = (lp(white(M), 170, 2) + 0.35 * bp(white(M), 150, 500)) * np.clip(0.75 + 0.35 * g, 0.2, None)
    bed = xfade_loop(bed, L); bed = bed / bed.std() * 0.02
    seed(301); ev = np.zeros(L)
    spots = [(1150, 5.5), (1500, 8.0), (900, 11.0)]          # three drip spots, each with its own pace
    for f0, gap in spots:
        for t in times(L_s, gap, gap * 0.5, jitter=0.35):
            f = f0 * (1 + R().uniform(-0.04, 0.04)); n = N(0.06)
            d = np.sin(2 * np.pi * np.cumsum(expsweep(f, f * 1.7, 0.06)) / SR) * expenv(n, 0.014, 0.001)
            d[:N(0.01)] += 0.2 * grain(0.01, 2000, 6000, 0.002)
            place(ev, d, t, R().uniform(0.10, 0.18), wrap=True)
    def echo(z):
        y = z + 0.35 * np.concatenate([np.zeros(N(0.055)), z[:-N(0.055)]])
        return y + delay(y, 0.37, fb=0.55, mix=0.8, damp=2200, nrep=10) - y
    ev = circ(echo, ev)
    return finish('cellar', bed + ev)

def pond_room(night):
    L_s = 59; L = N(L_s); M = L + N(XF_S)
    seed(400); bed = lp(white(M), 380, 2) * (1 + 0.1 * curve(L, M, kmax=4))
    bed = xfade_loop(bed, L); bed = bed / bed.std() * 0.016
    seed(401); ev = np.zeros(L); sets = curve(L, L, kmax=5)
    for t in times(L_s, 1.4, 0.7, jitter=0.5):
        dur = R().uniform(0.4, 0.9); n = N(dur); c = R().uniform(250, 700)
        sl = bp(white(n), c * 0.6, c * 1.6) * env_ar(n, dur * 0.3, dur * 0.65)
        if R().random() < 0.3:
            pb = np.sin(2 * np.pi * np.cumsum(expsweep(R().uniform(450, 700), 1200, 0.03)) / SR) * expenv(N(0.03), 0.008, 0.001)
            place(sl, pb * 0.25, N(R().uniform(0.05, dur * 0.6)))
        amp = 0.09 * (1.2 + 0.4 * sets[min(L - 1, N(t))])
        place(ev, sl, t, amp, wrap=True)
    if not night:
        seed(402); M2 = L + N(XF_S); gust = np.clip(curve(L, M2, kmax=7) * 0.6 + 0.5, 0, None) ** 2
        reeds = hp(lp(white(M2), 7000), 1800) * gust
        cr = np.zeros(M2)
        for i in np.nonzero(R().random(M2) < 0.0006 * gust / (gust.max() + 1e-9))[0]:
            place(cr, grain(0.006, 2500, 8000, 0.0015), int(i), R().uniform(0.3, 1.0))
        reeds = xfade_loop(reeds * 0.012 + cr * 0.03, L)
        ev = ev + reeds
    else:
        seed(403)
        for base, gap in [(310, 7.0), (520, 9.5)]:
            for t in times(L_s, gap, 3.5, jitter=0.5):
                call = np.zeros(N(1.0)); tt = 0.0
                for _ in range(R().integers(1, 4)):
                    d = R().uniform(0.12, 0.22); n = N(d); f = base * R().uniform(0.95, 1.05)
                    fr = expsweep(f * 1.08, f * 0.9, d)
                    am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * R().uniform(28, 40) * np.arange(n) / SR))
                    x = pulse(fr, d, 0.25) * am * env_ar(n, 0.02, 0.06)
                    place(call, lp(x, 2200), N(tt)); tt += d + R().uniform(0.08, 0.16)
                place(ev, call, t, R().uniform(0.05, 0.09), wrap=True)
    return finish('pond_room_night' if night else 'pond_room', bed + ev)

def nursery(night):
    L_s = 60; L = N(L_s); M = L + N(XF_S)
    seed(500); bed = xfade_loop(room_tone(M, L, 500, 0.04), L); bed = bed / bed.std() * 0.012
    ev = np.zeros(L)
    seed(501)
    for i, t in enumerate(np.arange(0, L_s, 0.5)):          # even tick-tock, 120 per loop
        n = N(0.03); f = 1900 if i % 2 == 0 else 1550
        tk = grain(0.03, 1500, 6000, 0.0018) * 0.6 + tri(f, 0.03, steps=False) * expenv(n, 0.005, 0.0004) * 0.5
        place(ev, lp(tk, 6000), float(t), 0.06, wrap=True)
    if night:
        seed(502); gaps = R().uniform(4.6, 5.6, 12); gaps *= L_s / gaps.sum()   # 12 breaths fit the loop
        t = 0.0
        for gp in gaps:
            ind = R().uniform(1.4, 1.8); exd = R().uniform(2.0, 2.5); a = R().uniform(0.85, 1.0)
            ni, ne = N(ind), N(exd)
            inh = bp(white(ni), 450, 2200) * np.sin(np.pi * np.arange(ni) / ni) ** 1.5
            exh = (lp(white(ne), 1100) + 0.4 * bp(white(ne), 300, 1600)) * (np.sin(np.pi * np.minimum(np.arange(ne) / ne * 1.6, 1)) ** 1.2) * np.linspace(1, 0.3, ne)
            place(ev, inh * 0.022 * a, t, wrap=True); place(ev, exh * 0.03 * a, t + ind + 0.15, wrap=True)
            t += gp
    return finish('nursery_night' if night else 'nursery', bed + ev)

def bee(T):
    n = N(T); t = np.arange(n) / SR; f0 = R().uniform(190, 250)
    cents = 150 * np.tanh((t - T / 2) / (T / 4)) * R().choice([-1, 1])            # pass glide
    for rate in (2.7, 4.3, 6.1):
        cents += 70 * np.sin(2 * np.pi * rate * R().uniform(0.8, 1.2) * t + R().uniform(0, 6.28))
    f = f0 * 2 ** (cents / 1200)
    am = 1 + 0.25 * np.sin(2 * np.pi * R().uniform(9, 15) * t) + 0.15 * curve(n, n, kmax=12)
    x = (0.6 * pulse(f, T, 0.3) + 0.4 * tri(f, T, steps=False)) * am
    return lp(x, 1600) * np.sin(np.pi * t / T) ** 2

def greenhouse(night):
    L_s = 64; L = N(L_s); M = L + N(XF_S)
    seed(600); bed = lp(white(M), 900, 2) * 0.8 + 0.05 * hp(lp(white(M), 6000), 2000)
    bed = xfade_loop(bed * (1 + 0.1 * curve(L, M, kmax=4)), L); bed = bed / bed.std() * 0.016
    ev = np.zeros(L)
    if not night:
        seed(601)
        for t in times(L_s, 19.0, 10.0, jitter=0.4):
            e = np.zeros(N(4.0)); tt = 0.0
            for _ in range(R().integers(1, 3)):
                d = R().uniform(0.6, 1.4); n = N(d)
                place(e, hp(lp(white(n), 9000), 2500) * env_ar(n, 0.04, 0.45), N(tt)); tt += d + 0.25
            place(ev, e, t, 0.05, wrap=True)
        seed(602)
        for t in times(L_s, 7.0, 2.5, jitter=0.7):
            T = R().uniform(1.5, 3.2); place(ev, bee(T), t, R().uniform(0.05, 0.09), wrap=True)
    else:
        seed(603); ev += cricket_field(L, [(4300, 0.55, 3, 0.022), (5000, 0.72, 4, 0.014)])
    return finish('greenhouse_night' if night else 'greenhouse', bed + ev)

def workshop():
    L_s = 69; L = N(L_s); M = L + N(XF_S)
    seed(700); bed = xfade_loop(room_tone(M, L, 800, 0.05), L); bed = bed / bed.std() * 0.016
    seed(701); ev = np.zeros(L)
    for t in times(L_s, 10.0, 5.0):
        d = R().uniform(0.4, 1.4); r0 = R().uniform(30, 70)
        c = creak(d, r0, r0 * R().uniform(1.4, 2.6), [(300, 700, 1.0), (900, 1600, 0.5)])
        place(ev, c, t, R().uniform(0.07, 0.12), wrap=True)
    seed(702)
    for t in times(L_s, 3.5, 1.2, jitter=0.8):
        e = np.zeros(N(1.2)); tt = 0.0
        for _ in range(R().integers(1, 5)):
            tk = grain(0.02, 2000, 6000, R().uniform(0.001, 0.0025))
            if R().random() < 0.4: tk = tk + 0.4 * tri(R().uniform(1200, 2800), 0.02, steps=False) * expenv(N(0.02), 0.004, 0.0005)
            place(e, tk, N(tt), R().uniform(0.4, 1.0)); tt += R().uniform(0.05, 0.3)
        place(ev, e, t, R().uniform(0.08, 0.14), wrap=True)
    return finish('workshop', bed + ev)

def attic():
    L_s = 73; L = N(L_s); M = L + N(XF_S)
    seed(800); g = curve(L, M, kmax=9, slope=0.8)
    gust = np.clip(0.6 + 0.25 * g, 0.3, None)
    fc = 250 + 900 * np.clip((g + 1.5) / 3.5, 0, 1) ** 1.5
    bed = lp_sweep(white(M), fc) * gust ** 1.5 + 0.2 * bp(white(M), 120, 400) * gust
    bed = xfade_loop(bed, L); bed = bed / bed.std() * 0.02
    seed(801); ev = np.zeros(L)
    gl = g[:L]; ds = 441; pk_ds = signal.argrelmax(gl[::ds], order=500)[0]   # >= 5 s apart (100 Hz grid)
    peaks = pk_ds * ds
    peaks = [p for p in peaks if gl[p] > 0.3][:7]
    for i, p in enumerate(peaks):                           # whistle on strong gusts: monotonic glides
        d = R().uniform(1.6, 2.6); n = N(d); up = i % 2 == 0
        st = R().uniform(10, 13)                                # >= ~4.5 semitones/s, never lingers
        f0 = R().uniform(620, 760); f1 = f0 * 2 ** ((st if up else -st) / 12)
        fr = f0 * (f1 / f0) ** np.linspace(0, 1, n) * (1 + 0.003 * curve(n, n, kmax=20))
        w = np.sin(2 * np.pi * np.cumsum(fr) / SR) * (1 + 0.25 * curve(n, n, kmax=25))
        w = w * np.sin(np.pi * np.arange(n) / n) ** 2 + 0.3 * bp(white(n), 500, 1500) * np.sin(np.pi * np.arange(n) / n) ** 2
        place(ev, w, p / SR - d / 2, 0.028 * min(1.3, gl[p]), wrap=True)
    seed(802)
    for t in times(L_s, 20.0, 12.0, jitter=0.4):
        d = R().uniform(1.0, 2.0); r0 = R().uniform(18, 35)
        c = creak(d, r0, r0 * R().uniform(1.3, 2.0), [(150, 450, 1.0), (500, 1100, 0.4)])
        place(ev, lp(c, 2500), t, R().uniform(0.08, 0.12), wrap=True)
    return finish('attic', bed + ev)

def bird_phrase():
    e = np.zeros(N(2.0)); tt = 0.0
    if R().random() < 0.5:                                  # species A: quick falling chirps
        for _ in range(R().integers(3, 7)):
            d = R().uniform(0.04, 0.08); n = N(d); f = R().uniform(3600, 4300)
            x = np.sin(2 * np.pi * np.cumsum(expsweep(f, f * 0.68, d)) / SR) * np.hanning(n)
            place(e, x, N(tt), R().uniform(0.7, 1.0)); tt += d + R().uniform(0.05, 0.1)
    else:                                                   # species B: 'tee-yoo'
        for f_a, f_b, d in [(2500, 3200, 0.15), (3000, 2200, 0.2)]:
            n = N(d); x = np.sin(2 * np.pi * np.cumsum(expsweep(f_a, f_b, d)) / SR) * np.hanning(n)
            place(e, x, N(tt)); tt += d + 0.04
        if R().random() < 0.5:
            tt += 0.25
            for f_a, f_b, d in [(2500, 3200, 0.15), (3000, 2200, 0.2)]:
                n = N(d); x = np.sin(2 * np.pi * np.cumsum(expsweep(f_a, f_b, d)) / SR) * np.hanning(n)
                place(e, x, N(tt), 0.8); tt += d + 0.04
    return lp(e, 7000)

def garden(night):
    L_s = 66; L = N(L_s); M = L + N(XF_S)
    seed(900); gust = np.clip(curve(L, M, kmax=8, slope=0.8) * 0.25 + 0.65, 0.35, None)
    leaves = hp(lp(white(M), 8000), 1200) * gust ** 1.6 + 0.4 * lp(white(M), 450) * gust
    cr = np.zeros(M)
    for i in np.nonzero(R().random(M) < 0.0004 * gust ** 2)[0]:
        place(cr, grain(0.008, 2000, 7000, 0.002), int(i), R().uniform(0.2, 1.0))
    bed = xfade_loop(leaves + 0.8 * cr, L); bed = bed / bed.std() * 0.02
    if night: bed = lp(bed, 3500) * 0.8              # same breeze, a little darker at night
    ev = np.zeros(L)
    if not night:
        seed(901)
        for t in times(L_s, 13.0, 7.0, jitter=0.5):        # ~5 phrases per loop, never overlapping
            place(ev, bird_phrase(), t, R().uniform(0.06, 0.1), wrap=True)
    else:
        seed(902); ev += cricket_field(L, [(3900, 0.5, 3, 0.02), (4500, 0.62, 3, 0.014), (5200, 0.8, 4, 0.01)])
    return finish('garden_night' if night else 'garden', bed + ev)

ROOMS = {'storeroom': lambda: storeroom(False), 'storeroom_night': lambda: storeroom(True),
         'music_room': music_room, 'cellar': cellar,
         'pond_room': lambda: pond_room(False), 'pond_room_night': lambda: pond_room(True),
         'nursery': lambda: nursery(False), 'nursery_night': lambda: nursery(True),
         'greenhouse': lambda: greenhouse(False), 'greenhouse_night': lambda: greenhouse(True),
         'workshop': workshop, 'attic': attic,
         'garden': lambda: garden(False), 'garden_night': lambda: garden(True)}
if __name__ == '__main__':
    for k in (sys.argv[1:] or ROOMS): ROOMS[k]()
