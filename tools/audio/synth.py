import numpy as np, wave, subprocess, os
from scipy import signal
SR = 44100
rng = np.random.default_rng(1987)

def N(d): return int(round(d * SR))
def bc(x, n): return np.broadcast_to(np.asarray(x, float), (n,)).copy()

def phase(f, n): return np.cumsum(bc(f, n)) / SR

def pulse(f, dur, duty=0.5):
    n = N(dur); ph = phase(f, n) % 1.0; d = bc(duty, n)
    return np.where(ph < d, 1.0, -1.0) - (2 * d - 1)   # remove DC per duty

def tri(f, dur, steps=True):
    n = N(dur); ph = phase(f, n) % 1.0
    t = 4 * np.abs(ph - 0.5) - 1
    if steps: t = np.round((t + 1) * 7.5) / 7.5 - 1   # NES-style 4-bit staircase
    return t

def noise(dur, rate=SR, short=False):
    n = N(dur); r = bc(rate, n)
    if np.all(r >= SR): return rng.choice([-1.0, 1.0], n)       # plain white noise
    r = r * rng.uniform(0.75, 1.25, n)    # jitter hold lengths: avoids periodic S&H pattern -> spectral lines
    idx = np.floor(np.cumsum(r) / SR).astype(int)
    if short:   # NES "metallic" mode: short repeating pattern
        pat = rng.choice([-1.0, 1.0], 93); return pat[idx % 93]
    vals = rng.choice([-1.0, 1.0], idx.max() + 1)
    return vals[idx]

def adsr(n, a=0.005, d=0.05, s=0.7, r=0.03, gate=None):
    gate = n if gate is None else min(gate, n)
    A, D, R = max(1, N(a)), max(1, N(d)), max(1, N(r))
    i = np.arange(n, dtype=float)
    e = np.where(i < A, i / A, np.where(i < A + D, 1 - (1 - s) * (i - A) / D, s))
    lvl = e[gate - 1] if gate > 0 else 0.0
    rel = i >= gate
    e[rel] = lvl * np.clip(1 - (i[rel] - gate) / R, 0, None)
    return e

def expenv(n, tau, a=0.002):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1.0) * np.exp(-t / tau)

def fade(x, fi=0.003, fo=0.01):
    x = x.copy(); a, b = min(N(fi), len(x)), min(N(fo), len(x))
    if a: x[:a] *= np.linspace(0, 1, a)
    if b: x[-b:] *= np.linspace(1, 0, b)
    return x

def lp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, 'low', fs=SR, output='sos'), x)
def hp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)

def lp_sweep(x, fc):
    """one-pole lowpass with time-varying cutoff"""
    fc = bc(fc, len(x)); a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s += a[i] * (x[i] - s); y[i] = s
    return y

def expsweep(f0, f1, dur, n=None):
    n = N(dur) if n is None else n
    return f0 * (f1 / f0) ** np.linspace(0, 1, n)

def place(buf, x, t, gain=1.0, wrap=False):
    i = N(t) if isinstance(t, float) else int(t)
    if wrap:
        idx = (np.arange(len(x)) + i) % len(buf); np.add.at(buf, idx, x * gain); return
    end = min(len(buf), i + len(x))
    if end > i: buf[i:end] += x[:end - i] * gain

def delay(x, dt, fb=0.4, mix=0.5, damp=3500, nrep=8):
    out = x.copy(); rep = x.copy(); D = N(dt)
    for k in range(1, nrep + 1):
        rep = lp(rep, damp, 1) * fb
        if np.max(np.abs(rep)) < 1e-4: break
        s = np.zeros_like(x); s[D * k:] = rep[:len(x) - D * k] if D * k < len(x) else 0
        out += s * mix
    return out

NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
def midi(name):
    l, rest = name[0], name[1:]; acc = 0
    while rest and rest[0] in '#b':
        acc += 1 if rest[0] == '#' else -1; rest = rest[1:]
    return 12 * (int(rest) + 1) + NOTE[l] + acc
def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def fq(name): return hz(midi(name))

def parse(s):
    out = []
    for tok in s.split():
        n, st = tok.split(':'); out.append((None if n == 'R' else midi(n), float(st)))
    return out

def normalize(x, peak_db=-1.0):
    return x / np.max(np.abs(x)) * 10 ** (peak_db / 20)

def write(path_noext, x):
    assert np.all(np.isfinite(x))
    pcm = np.clip(np.round(x * 32767), -32768, 32767).astype('<i2')   # (n,) mono or (n,2) stereo interleaved
    with wave.open(path_noext + '.wav', 'wb') as w:
        w.setnchannels(1 if x.ndim == 1 else x.shape[1]); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


# ---------------- loudness / mastering helpers (house-audio) ----------------
import pyloudnorm as pyln
from scipy.ndimage import minimum_filter1d
_METER = pyln.Meter(SR)

def lufs(x):
    """BS.1770-4 integrated loudness (pyloudnorm). Files shorter than one 400 ms gating
    block are zero-padded to 0.4 s (documented fallback for very short sounds)."""
    if len(x) < N(0.4): x = np.concatenate([x, np.zeros(N(0.4) - len(x))])
    return _METER.integrated_loudness(x)

def true_peak_db(x):
    """4x oversampled peak (BS.1770 true-peak approximation)."""
    y = signal.resample_poly(x, 4, 1, axis=0)
    return 20 * np.log10(np.max(np.abs(y)) + 1e-12)

def limiter(x, ceiling_db=-1.3, look=0.0015, release=0.06):
    """Lookahead peak limiter on the 4x-oversampled envelope (gain only, no clipping)."""
    c = 10 ** (ceiling_db / 20)
    up = np.abs(signal.resample_poly(x, 4, 1, axis=0))
    ax = np.abs(x)
    if x.ndim > 1: up = up.max(axis=1); ax = ax.max(axis=1)      # stereo-linked
    pk = up[:len(x) * 4].reshape(-1, 4).max(axis=1)
    pk = np.maximum(pk, ax)
    g = np.minimum(1.0, c / (pk + 1e-12))
    L = max(1, N(look))
    g = minimum_filter1d(g, size=2 * L + 1)           # gain floor reached before the peak
    a = np.exp(-1 / (release * SR)); out = np.empty_like(g); s_ = 1.0
    for i in range(len(g)):                            # instant attack (already looked-ahead), smooth release
        s_ = g[i] if g[i] < s_ else a * s_ + (1 - a) * g[i]
        out[i] = s_
    sm = np.convolve(out, np.ones(L) / L, mode='same')  # smooth attack corners
    g = np.minimum(sm, out)
    return x * (g[:, None] if x.ndim > 1 else g)

def level(x, target, ceiling_db=-1.0, tol=0.1, release=0.03):
    """Gain to integrated-LUFS target; if true peak would exceed the ceiling, limit and iterate."""
    for _ in range(20):
        x = x * 10 ** ((target - lufs(x)) / 20)
        if true_peak_db(x) > ceiling_db - 0.2:
            x = limiter(x, ceiling_db - 0.4, release=release)
        if abs(lufs(x) - target) < tol and true_peak_db(x) <= ceiling_db - 0.1:
            break
    return x

def trim_sfx(x, thresh_db=-60, tail_keep=0.03, fade_out=0.025):
    """No lead silence; trailing content below thresh (rel. peak) cut; short fade-out."""
    th = np.max(np.abs(x)) * 10 ** (thresh_db / 20)
    nz = np.where(np.abs(x) > th)[0]
    x = x[nz[0]: min(len(x), nz[-1] + N(tail_keep))].copy()
    x[:16] *= np.linspace(0, 1, 16)                   # 0.36 ms de-click at onset
    f = min(N(fade_out), len(x)); x[-f:] *= np.linspace(1, 0, f) ** 2
    return x

def loop_finalize(x, near=0, search=0.006, edge=32):
    """x is already circular (seamless). Rotate to the upward zero crossing nearest `near`
    (within +-search s) so the file starts/ends at ~0, then a tiny 32-sample taper -> exactly 0."""
    n = len(x); S = N(search); best = None
    xm = x.mean(axis=1) if x.ndim > 1 else x            # stereo: search on the mid signal
    xa = np.abs(x).max(axis=1) if x.ndim > 1 else np.abs(x)
    for k in range(-S, S):
        i = (near + k) % n
        if xm[i - 1] < 0 <= xm[i]:
            score = xa[i] + xa[i - 1] + 1e-4 * abs(k)
            if best is None or score < best[0]: best = (score, i)
    i = best[1] if best else near % n
    y = np.roll(x, -i, axis=0).copy()
    r = np.sin(np.linspace(0, np.pi / 2, edge)) ** 2
    if y.ndim > 1: r = r[:, None]
    y[:edge] *= r; y[-edge:] *= r[::-1]
    return y, i
