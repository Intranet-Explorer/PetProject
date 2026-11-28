"""ambience/machine_room.wav - soft ticking & clicks, no hum (batch 0 rework of computer_room_ambience_loop;
batch 2 adds a soft even tick layer).
Removed vs. original: 60/120/180 Hz mains/CRT hum and the 7.87 kHz flyback whine.
Kept: broadband fan/air noise bed (crossfaded seam), drive-seek click bursts, soft beeps,
short modem chirps, keyboard clacks. Events are placed circularly so the loop is seamless."""
from synth import *
OUT = '/workspace/house-audio/ambience'; os.makedirs(OUT, exist_ok=True)
TARGET = -28.0
L_S = 48.0; L = N(L_S)
ev = np.zeros(L)

# --- noise bed only (no tonal components) ---
XF = N(2.0); n = L + XF; t = np.arange(n) / SR
fan = lp(noise(n / SR, 44100), 500, 2) + 0.3 * bp(noise(n / SR, 44100), 900, 2200)
fan *= 1 + 0.12 * np.sin(2 * np.pi * (3 / L_S) * t)          # slow airflow drift, integer cycles per loop
fan = fan / np.std(fan) * 0.02
ramp = np.linspace(0, np.pi / 2, XF)
bed = fan[:L].copy()
bed[:XF] = fan[:XF] * np.sin(ramp) + fan[L:L + XF] * np.cos(ramp)   # equal-power seam crossfade

def seek_burst():
    k = rng.integers(2, 7); out = np.zeros(N(0.6)); tt = 0.0
    for _ in range(k):
        n = N(0.02)
        c = bp(noise(0.02, 44100), 1200, 5000) * expenv(n, 0.0025, 0.0003)
        th = tri(rng.uniform(90, 140), 0.02, steps=False) * expenv(n, 0.006, 0.0005)
        place(out, c * 0.6 + th * 0.5, tt); tt += rng.uniform(0.025, 0.09)
    return out

def beep():
    f = rng.choice([fq('C6'), fq('G5'), fq('E6'), fq('A5')])
    k = rng.integers(1, 3); out = np.zeros(N(0.5)); tt = 0
    for i in range(k):
        x = pulse(f * (1.5 if i else 1), 0.07, 0.25) * adsr(N(0.07), 0.003, 0.02, 0.7, 0.01, N(0.06))
        place(out, lp(x, 3500), tt); tt += 0.11
    return out

def modem(dur):
    out = np.zeros(N(dur) + N(0.05)); tt = 0.0
    while tt < dur:
        d = rng.uniform(0.02, 0.06)
        f = rng.choice([1070, 1270, 1650, 1850, 2100, 2225, 2400])
        x = pulse(f * 2 ** (rng.uniform(-0.3, 0.3) / 12), d, rng.choice([0.25, 0.5])) * adsr(N(d), 0.003, 0.01, 0.8, 0.004, N(d) - N(0.004))
        place(out, x, tt); tt += d
    hiss = bp(noise(dur, 22000), 1000, 3000) * 0.25
    out[:len(hiss)] += hiss * np.sin(np.pi * np.linspace(0, 1, len(hiss)))
    return lp(fade(out, 0.01, 0.03), 3500)

def typing(nk):
    out = np.zeros(N(nk * 0.5 + 1)); tt = 0.0
    for i in range(nk):
        space = rng.random() < 0.15; n = N(0.04)
        body = lp(noise(0.04, 44100), 1400 if space else 2800) * expenv(n, 0.006 if space else 0.004, 0.0005)
        top = hp(noise(0.04, 44100), 3500) * expenv(n, 0.0015, 0.0003)
        thock = tri(rng.uniform(140, 200) if space else rng.uniform(250, 380), 0.04, steps=False) * expenv(n, 0.008, 0.0005)
        place(out, body * 0.5 + top * 0.25 + thock * 0.35, tt, rng.uniform(0.6, 1.0))
        tt += rng.choice([rng.uniform(0.07, 0.16), rng.uniform(0.25, 0.5)], p=[0.85, 0.15])
    return out[:N(tt + 0.1)]

starts = np.arange(1.5, L_S, 5.5)
for s in starts + rng.uniform(-1.5, 1.5, len(starts)):
    place(ev, seek_burst(), float(s % L_S), 0.09, wrap=True)
for s in [6.3, 19.8, 31.2, 44.1]:
    place(ev, beep(), s, 0.03, wrap=True)
for s, d in [(14.0, 0.9), (37.5, 0.6)]:
    place(ev, modem(d), s, 0.018, wrap=True)
for s, k in [(3.0, 14), (11.5, 9), (22.0, 22), (34.0, 7), (40.5, 15)]:
    place(ev, typing(k), s, 0.12, wrap=True)

# batch 2: soft, even ticking (brief: 'soft ticking and clicks, no hum'); seeded after all other events
# so the rest of the loop is unchanged. 0.75 s period -> exactly 64 ticks per 48 s loop.
for i, t in enumerate(np.arange(0, L_S, 0.75)):
    n = N(0.025)
    tk = bp(noise(0.025, 44100), 1800, 5000) * expenv(n, 0.0015, 0.0003)
    tk += 0.35 * tri(1350 if i % 2 else 1250, 0.025, steps=False) * expenv(n, 0.004, 0.0004)
    place(ev, lp(tk, 5000), float(t), 0.028 * rng.uniform(0.85, 1.0), wrap=True)

mix = bed + ev
mix = hp(np.concatenate([mix, mix]), 30)[L:]          # circular high-pass (filter 2 loops, keep the 2nd)
mix, rot = loop_finalize(mix, near=0)                # start/end on a zero crossing, exact-zero edges
mix = level(mix, TARGET)
write(f'{OUT}/machine_room', mix)
print('machine_room', len(mix) / SR, 's', round(lufs(mix), 2), 'LUFS', round(true_peak_db(mix), 2), 'dBTP rot', rot)
