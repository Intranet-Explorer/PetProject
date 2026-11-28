"""The hob voice: Animal-Crossing-style babble from one consistent synthetic 'voice'.
Source = 70% pulse (duty 0.33) + 30% triangle at a cute-but-warm base pitch (~480 Hz), plus a
little breath noise; colored by vowel formants (F1/F2/F3 band-passes, scaled x1.18 for a small
creature) with optional vowel glides; per-syllable pitch contours; soft consonant-like onsets
(noise burst, pitch blip, nasal 'm' opening). Everything that speaks in batch 4 uses syl()/voiced()."""
import synth as S
from synth import *

BASE = 480.0                     # Hz, the hob's speaking pitch
FS = 1.18                        # formant scale (small vocal tract)
VOW = {'a': (800, 1250, 2600), 'e': (480, 1950, 2700), 'i': (320, 2350, 3000),
       'o': (520, 880, 2500), 'u': (360, 720, 2400), 'm': (280, 1100, 2400)}
VOWEL_W = {'a': 0.28, 'e': 0.22, 'i': 0.18, 'o': 0.18, 'u': 0.14}

def seed(s): S.rng = np.random.default_rng(s)
def R(): return S.rng

def formant(src, v):
    F1, F2, F3 = [x * FS for x in VOW[v]]
    y = bp(src, F1 * 0.78, F1 * 1.28) + 0.55 * bp(src, F2 * 0.86, F2 * 1.16) + 0.18 * bp(src, F3 * 0.9, F3 * 1.1)
    if v == 'm': y = 0.4 * y + lp(src, 700)          # closed mouth: mostly low hum
    return y + 0.22 * lp(src, 1300)                  # keep warmth/body for every vowel

def voiced(cents, vowels, breath=0.06, duty=0.33, base=BASE):
    """cents: per-sample pitch curve (relative to base). vowels: [(t_frac, 'a'), ...] path."""
    n = len(cents); d = n / SR; f = base * 2 ** (cents / 1200)
    src = 0.7 * pulse(f, d, duty) + 0.3 * tri(f, d, steps=False) + breath * R().normal(0, 1, n)
    names = sorted(set(v for _, v in vowels)); outs = {v: formant(src, v) for v in names}
    tf = np.linspace(0, 1, n); y = np.zeros(n)
    pts = [p for p, _ in vowels]
    for v in names:   # piecewise-linear weights along the vowel path
        w = np.interp(tf, pts, [1.0 if vv == v else 0.0 for _, vv in vowels]) if len(vowels) > 1 else np.ones(n)
        y += w * outs[v]
    return lp(y, 6000)

def contour(n, kind, amt):
    t = np.linspace(0, 1, n)
    if kind == 'rise': c = amt * t
    elif kind == 'fall': c = -amt * t
    elif kind == 'arch': c = amt * np.sin(np.pi * t) - 0.3 * amt * t
    elif kind == 'dip': c = -amt * np.sin(np.pi * t)
    else: c = 0.3 * amt * (t - 0.5)
    return c * 100.0   # semitones -> cents

def syl(dur, offset_st=0.0, vowel=None, kind=None, amt=None, onset=None, amp=1.0, vowel2=None, breath=0.06, base=BASE):
    """One babble syllable (~70-160 ms)."""
    n = N(dur)
    vowel = vowel or R().choice(list(VOWEL_W), p=list(VOWEL_W.values()))
    kind = kind or R().choice(['rise', 'fall', 'arch', 'dip', 'flat'], p=[0.22, 0.3, 0.22, 0.1, 0.16])
    amt = R().uniform(1.0, 3.0) if amt is None else amt
    onset = onset or R().choice(['none', 'noise', 'blip', 'nasal'], p=[0.35, 0.25, 0.25, 0.15])
    c = offset_st * 100 + contour(n, kind, amt)
    if onset == 'blip': c += 450 * np.exp(-np.arange(n) / SR / 0.012)
    path = [(0, vowel)] if vowel2 is None else [(0, vowel), (1, vowel2)]
    if onset == 'nasal': path = [(0, 'm'), (min(0.3, 0.025 / dur), 'm'), (min(0.6, 0.06 / dur), vowel)] + ([(1, vowel2)] if vowel2 else [])
    y = voiced(c, path, breath, base=base)
    y *= adsr(n, 0.007, dur * 0.5, 0.75, min(0.03, dur * 0.3), n - N(min(0.03, dur * 0.3)))
    if onset == 'noise':
        nb = N(R().uniform(0.012, 0.022)); burst = bp(R().normal(0, 1, nb), 2500, 7000) * np.hanning(nb) * 0.35
        y = np.concatenate([burst, y])
    return y * amp

def breath_noise(dur, lo, hi, shape='sin', vowel=None):
    n = N(dur); x = bp(R().normal(0, 1, n), lo, hi)
    if vowel: x = formant(x, vowel)
    t = np.linspace(0, 1, n)
    e = np.sin(np.pi * t) ** 1.5 if shape == 'sin' else np.minimum(t / 0.15, 1) * (1 - t) ** 1.2
    return x * e

def babble(seed_, mode='statement', max_s=1.85, n_syl=None, base=BASE, return_parts=False):
    """A sentence: random syllables with declination, word gaps, and a mode-dependent ending."""
    seed(seed_)
    n_syl = n_syl or int(R().integers(4, 10))
    lift = {'statement': 0.0, 'question': 0.5, 'exclaim': 3.0}[mode]
    out = []; t = 0.0; off = R().uniform(-1, 1); prev = None
    for i in range(n_syl):
        last = i == n_syl - 1
        dur = R().uniform(0.07, 0.16)
        step = R().uniform(1.0, 3.0) * R().choice([-1, 1])            # always move >= 1 st: speech-like, never chains
        off = np.clip(off + step, -3.5, 4.0); decl = -2.2 * i / max(1, n_syl - 1)
        kw = {}
        if last:
            dur = R().uniform(0.15, 0.2)
            if mode == 'question': kw = dict(kind='rise', amt=R().uniform(4.5, 6.0))
            elif mode == 'exclaim': kw = dict(kind='fall', amt=R().uniform(4.0, 6.0), amp=1.25)
            else: kw = dict(kind='fall', amt=R().uniform(1.5, 3.0))
        amp = (1.2 if mode == 'exclaim' else 1.0) * R().uniform(0.8, 1.0)
        kw.setdefault('amp', amp)
        y = syl(dur, off + decl + lift, base=base, **kw)
        gap = R().uniform(0.025, 0.045) + (R().uniform(0.05, 0.09) if R().random() < 0.22 and not last else 0)
        if t + len(y) / SR > max_s: break
        out.append((t, y)); t += len(y) / SR + gap
    buf = np.zeros(N(t + 0.1))
    for tt, y in out: place(buf, y, tt)
    return buf

if __name__ == '__main__':
    # review demos (not deliverables): reports/voice_demo_*.wav
    import os; RD = '/workspace/house-audio/reports'; os.makedirs(RD, exist_ok=True)
    demos = {'voice_demo_1_statements': [(11, 'statement', 8), (12, 'statement', 6), (13, 'statement', 9)],
             'voice_demo_2_questions': [(21, 'question', 5), (22, 'question', 7), (23, 'question', 4)],
             'voice_demo_3_exclamations': [(31, 'exclaim', 4), (32, 'exclaim', 6), (33, 'exclaim', 3)],
             'voice_demo_4_conversation': [(41, 'statement', 9), (42, 'question', 6), (43, 'statement', 7),
                                           (44, 'exclaim', 4), (45, 'statement', 10), (46, 'question', 5)]}
    for name, sents in demos.items():
        parts = [babble(s, m, max_s=3.0, n_syl=k) for s, m, k in sents]
        gap = np.zeros(N(0.55)); y = np.concatenate(sum([[p, gap] for p in parts], []))
        y = level(trim_sfx(hp(y, 60)), -16.0); write(f'{RD}/{name}', y)
        print(name, round(len(y) / SR, 2), 's')
