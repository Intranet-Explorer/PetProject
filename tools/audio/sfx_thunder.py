"""sfx/thunder_1..3: near crack + rumble -> distant low roll. Noise only (no tones).
Level: -16 LUFS integrated (BS.1770-4), <= -1 dBTP, starts immediately, short fade, trimmed tail."""
import synth as S
from synth import *
OUT = '/workspace/house-audio/sfx'

def seed(s): S.rng = np.random.default_rng(s)
def brown(n):
    return lp(S.rng.normal(0, 1, n), 60, 1) * 8 + lp(S.rng.normal(0, 1, n), 400, 2)

def rolls(n, k, spread, tau):
    """Irregular rolling envelope: k overlapping swells with random onsets/heights, overall decay."""
    t = np.arange(n) / SR; e = np.zeros(n)
    for _ in range(k):
        c = S.rng.uniform(0, spread); w = S.rng.uniform(0.15, 0.6); h = S.rng.uniform(0.4, 1.0)
        e += h * np.exp(-0.5 * ((t - c) / w) ** 2)
    return (0.25 + e) * np.exp(-t / tau)

def thunder(near, dur, sd):
    seed(sd); n = N(dur); t = np.arange(n) / SR; out = np.zeros(n)
    if near > 0.3:                                       # crack / tearing
        tt = 0.0
        for i in range(S.rng.integers(4, 8)):
            m = N(0.12); c = S.rng.normal(0, 1, m) * expenv(m, S.rng.uniform(0.01, 0.035), 0.001)
            c = lp(c, 2000 + 6000 * near)
            place(out, c, N(tt), (1.0 if i == 0 else S.rng.uniform(0.3, 0.7)) * near); tt += S.rng.uniform(0.02, 0.09)
    fc = (150 + 900 * near) * (1 / (1 + t * (1.0 + near)))      # rumble darkens as it rolls away
    rum = lp_sweep(brown(n), fc + 60)
    rum *= rolls(n, int(5 + 6 * near), dur * (0.5 + 0.2 * (1 - near)), dur * (0.35 + 0.25 * (1 - near)))
    att = np.minimum(t / (0.003 if near > 0.3 else 0.12), 1)
    out += rum / (np.std(rum) + 1e-12) * 0.25 * att
    f = N(0.6); out[-f:] *= np.linspace(1, 0, f) ** 2
    return hp(out, 25)

if __name__ == '__main__':
    for name, near, dur, sd in [('thunder_1', 1.0, 4.9, 2001), ('thunder_2', 0.55, 4.9, 2002), ('thunder_3', 0.1, 4.9, 2003)]:
        x = level(trim_sfx(thunder(near, dur, sd), tail_keep=0.03, fade_out=0.06), -16.0)
        write(f'{OUT}/{name}', x)
        print(f'{name:10s} {len(x)/SR:5.2f}s {lufs(x):6.2f} LUFS {true_peak_db(x):6.2f} dBTP')
