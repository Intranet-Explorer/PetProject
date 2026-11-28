#!/usr/bin/env python3
"""Verify every WAV under /workspace/house-audio (or a given root) against the house-audio spec.
Usage: python3 check.py [root] [--json out.json]
Reports: format, duration, integrated LUFS (BS.1770-4 / pyloudnorm), 4x-oversampled true peak,
lead/trail silence, loop seam & edge values, longest steady tone, ambience tonal-peak test."""
import sys, os, re, glob, json, wave
import numpy as np
from scipy import signal
from scipy.ndimage import median_filter
import pyloudnorm as pyln

ROOT = next((a for a in sys.argv[1:] if not a.startswith('--') and not a.endswith('.json')), '/workspace/house-audio')
SR = 44100
TARGET = {'music': -20, 'ambience': -28, 'sfx': -16, 'jingles': -16, 'ui': -16}
LUFS_TOL = 1.0
DUR = {'music': (60, 120), 'ambience': (45, 90), 'sfx': (0, 2.0), 'jingles': (1, 4), 'ui': (0, 2.0)}
# per-file overrides: (min_s, max_s) length; files in STEADY_EXEMPT report held tones but aren't flagged
DUR_OVERRIDE = {'jingles/dawn.wav': (5, 10), 'jingles/dusk.wav': (5, 10)}   # brief table: 5-10 s transitions
DUR_PATTERNS = [(r'sfx/thunder_\d+\.wav', (0, 5.0))]                    # brief: thunder sfx up to 5 s
STEADY_EXEMPT = {'jingles/dawn.wav', 'jingles/dusk.wav',                     # one-off transitions, not often-played
                 'jingles/first.wav', 'jingles/invention.wav', 'jingles/project_done.wav', 'jingles/new_era.wav',
                 'jingles/something_new.wav', 'jingles/birth.wav', 'jingles/death.wav'}   # batch 7 one-off event jingles: held notes reported, not flagged
# per-file loudness targets (deviation, batch 7): brief says click/hover 'very quiet' and gives no ui target -> -24 LUFS
FILE_TARGET = {'ui/click.wav': -24, 'ui/hover.wav': -24}
# looping sfx (brief batch 6): exact stated length (+-1 ms), seamless + zero edges, steady-tone rule still applies,
# no lead/trail-silence rule (they loop)
LOOP_SFX = {'sfx/kiln_fire.wav': 10, 'sfx/loom.wav': 6, 'sfx/millstone.wav': 8, 'sfx/stove_sizzle.wav': 6,
            'sfx/pot_bubble.wav': 6, 'sfx/train_chug.wav': 4, 'sfx/sweeper_whir.wav': 4,
            'sfx/argue.wav': 4, 'sfx/scuffle.wav': 4}                         # batch 9
LOOPS = {'music', 'ambience'}
SHORT = {'sfx', 'jingles', 'ui'}            # "often-played short sounds"
SIL_DB = -60.0                              # silence threshold, dBFS
STEADY_MAX = 0.3

def read(p):
    with wave.open(p) as w:
        fmt = (w.getframerate(), w.getsampwidth() * 8, w.getnchannels())
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float) / 32768
    if fmt[2] > 1: x = x.reshape(-1, fmt[2])
    return x, fmt

def lufs(x, meter=pyln.Meter(SR)):
    note = ''
    if x.shape[0] < int(0.4 * SR):   # shorter than one gating block: zero-pad (silence is gated out)
        pad = np.zeros((int(0.4 * SR) - x.shape[0],) + x.shape[1:]); x = np.concatenate([x, pad]); note = 'padded'
    return meter.integrated_loudness(x), note

def true_peak(x):
    y = signal.resample_poly(x, 4, 1, axis=0)
    return 20 * np.log10(np.abs(y).max() + 1e-12)

def silence(m):
    th = 10 ** (SIL_DB / 20); nz = np.where(np.abs(m) > th)[0]
    if len(nz) == 0: return len(m) / SR, len(m) / SR
    return nz[0] / SR, (len(m) - 1 - nz[-1]) / SR

def seam(m):
    d = np.abs(np.diff(m)); j = abs(m[0] - m[-1])
    return j, float((d < j).mean() * 100)          # jump, percentile among normal sample steps

def steady_tone(m, nfft=2048, hop=441, rel_db=-35, prom_db=12, cents=50, step_cents=20, top=6, fmax=16000, sustain_db=6.0):
    """Held-tone detector. Tracks narrow spectral peaks (>12 dB above a 31-bin median, within 35 dB
    of the file's loudest STFT bin, 6 strongest per frame, 40-16000 Hz). A run continues while a peak
    stays within +-50 cents of the run's starting pitch, moves <= 20 cents per 10 ms frame and has
    gaps <= 20 ms (vibrato inside +-50 cents counts as held; glides break the run).
    'steady' = frames of the run whose level is within 6 dB of the run's running maximum, i.e. the
    SUSTAINED part of a tone. A free-decaying tone (bell, chime, pluck) stops counting once it has
    fallen 6 dB, so a struck chime with tau ~0.35 s scores ~0.25 s, while a held/swelling note, hum or
    whine scores its full length. 'ring' = raw run length including the decay (informational).
    Durations include ~46 ms window smear. Returns (steady_s, Hz, ring_s)."""
    if len(m) < nfft: m = np.pad(m, (0, nfft - len(m)))
    f, t, Z = signal.stft(m, SR, window='hann', nperseg=nfft, noverlap=nfft - hop, boundary=None, padded=False)
    db = 20 * np.log10(np.abs(Z) + 1e-10)
    ref = db.max(); lo, hi = int(40 * nfft / SR), int(fmax * nfft / SR)
    runs, best, ring = [], (0.0, 0.0), 0.0
    for k in range(db.shape[1]):
        col = db[:, k]; base = median_filter(col, 31)
        pk = signal.argrelmax(col)[0]
        pk = pk[(pk > lo) & (pk < hi) & (col[pk] > ref + rel_db) & (col[pk] - base[pk] > prom_db)]
        pk = pk[np.argsort(col[pk])[::-1][:top]]
        peaks = []
        for bb in pk:   # parabolic interpolation
            a_, c_, e_ = col[bb - 1], col[bb], col[bb + 1]; off = 0.5 * (a_ - e_) / (a_ - 2 * c_ + e_ + 1e-12)
            peaks.append(((bb + off) * SR / nfft, c_))
        new = []
        for fr, lv in peaks:
            hit = None
            for r in runs:     # r = [f0, k0, klast, flast, runmax, sustain_frames]
                if (r[2] >= k - 2 and r[2] < k and abs(1200 * np.log2(fr / r[0])) < cents
                        and abs(1200 * np.log2(fr / r[3])) < step_cents): hit = r; break
            if hit:
                hit[2] = k; hit[3] = fr; hit[4] = max(hit[4], lv)
                if lv >= hit[4] - sustain_db: hit[5] += 1
            else: new.append([fr, k, k, fr, lv, 1])
        runs = [r for r in runs if r[2] >= k - 2] + new
        for r in runs:
            s_ = r[5] * hop / SR; ring = max(ring, (r[2] - r[1] + 1) * hop / SR)
            if s_ > best[0]: best = (s_, r[0])
    return best[0], best[1], ring

def dips(m, win_s=0.005, ctx_s=0.2, depth=12.0, min_s=0.010):
    """Short level dips: 5 ms RMS frames more than `depth` dB below the 200 ms running median,
    lasting >= 10 ms (catches note-boundary gaps in sustained music). Returns [(t, ms, dB)]."""
    w = int(win_s * SR); k = len(m) // w
    r = 20 * np.log10(np.sqrt((m[:k * w].reshape(k, w) ** 2).mean(1)) + 1e-9)
    d = r - median_filter(r, int(ctx_s / win_s) | 1, mode='wrap')
    out, i = [], 0
    while i < k:
        if d[i] < -depth:
            j = i
            while j < k and d[j] < -depth: j += 1
            if (j - i) * win_s >= min_s: out.append((round(i * win_s, 3), int((j - i) * win_s * 1000), round(float(d[i:j].min()), 1)))
            i = j
        else: i += 1
    return out

def tonal_peaks(m, prom=10.0):
    """Long-term spectrum (Welch, 5.4 Hz bins): narrow peaks > `prom` dB above a 101-bin median."""
    f, P = signal.welch(m, SR, nperseg=8192)
    db = 10 * np.log10(P + 1e-20); base = median_filter(db, 101)
    sel = (f > 20) & (f < 16000)
    pk = signal.argrelmax(db)[0]
    pk = [p for p in pk if sel[p] and db[p] - base[p] > prom]
    return [(round(float(f[p]), 1), round(float(db[p] - base[p]), 1)) for p in pk]

def check(p):
    rel = os.path.relpath(p, ROOT); cat = rel.split(os.sep)[0]
    x, (sr, bits, ch) = read(p); m = x.mean(axis=1) if x.ndim > 1 else x
    r = {'file': rel, 'cat': cat, 'sr': sr, 'bits': bits, 'ch': ch, 'dur': len(m) / sr}
    r['lufs'], r['lufs_note'] = lufs(x); r['tp'] = true_peak(x); r['sp'] = 20 * np.log10(np.abs(x).max() + 1e-12)
    r['lead'], r['trail'] = silence(m)
    r['seam_jump'], r['seam_pct'] = seam(m); r['edge'] = (float(m[0]), float(m[-1]))
    r['steady'], r['steady_hz'], r['ring'] = steady_tone(m)
    r['tonal'] = tonal_peaks(m) if cat == 'ambience' else []
    r['dips'] = dips(m) if cat == 'music' else []
    r['corr'] = None
    v = []
    if (sr, bits) != (44100, 16): v.append('format')
    if ch != 1 and not (cat == 'music' and ch == 2): v.append('channels')
    if not re.fullmatch(r'[a-z0-9_]+\.wav', os.path.basename(p)): v.append('name')
    if not np.all(np.isfinite(x)): v.append('nan')
    tgt = FILE_TARGET.get(rel, TARGET.get(cat)); r['target'] = tgt
    if tgt is not None and abs(r['lufs'] - tgt) > LUFS_TOL: v.append(f"lufs({tgt})")
    if r['tp'] > -1.0: v.append('peak>-1dBTP')
    lo_hi = DUR_OVERRIDE.get(rel, next((v for pat, v in DUR_PATTERNS if re.fullmatch(pat, rel)), DUR.get(cat)))
    if rel in LOOP_SFX: lo_hi = (LOOP_SFX[rel] - 0.001, LOOP_SFX[rel] + 0.001)
    if lo_hi and not (lo_hi[0] <= r['dur'] <= lo_hi[1]): v.append('length')
    if ch == 2:   # mono compatibility: L/R correlation and loudness change of the mono fold-down
        r['corr'] = float(np.corrcoef(x[:, 0], x[:, 1])[0, 1])
        r['mono_delta'] = lufs(np.stack([m, m], 1))[0] - r['lufs']   # (L+R)/2 played on both speakers; 0 = no loss
        if r['corr'] < 0.3: v.append('stereo_corr<0.3')
    if cat in SHORT:
        if rel not in LOOP_SFX:
            if r['lead'] > 0.005: v.append('lead_silence')
            if r['trail'] > 0.1: v.append('trail_silence')
        if r['steady'] > STEADY_MAX and rel not in STEADY_EXEMPT: v.append('steady_tone>0.3s')
    if cat in LOOPS or rel in LOOP_SFX:
        if r['seam_pct'] > 99.0: v.append('seam_click')
        if max(abs(r['edge'][0]), abs(r['edge'][1])) > 1e-3: v.append('edge_not_zero')
    if cat == 'ambience':
        if r['steady'] > STEADY_MAX: v.append('steady_tone>0.3s')
    if r['dips']: v.append(f"dips({len(r['dips'])})")
    r['violations'] = v
    return r

if __name__ == '__main__':
    files = sorted(p for p in glob.glob(os.path.join(ROOT, '*', '*.wav'))
                   if os.path.relpath(p, ROOT).split(os.sep)[0] not in ('reports', 'src'))   # review renders aren't deliverables
    rows = [check(p) for p in files]
    hdr = f"{'file':42s} {'fmt':>11s} {'dur s':>6s} {'LUFS':>6s} {'dBTP':>6s} {'lead':>5s} {'trail':>5s} {'seam%':>6s} {'edge':>13s} {'steady':>11s}  status"
    print(hdr); print('-' * len(hdr))
    for r in rows:
        fmt = f"{r['sr']//1000}.1k/{r['bits']}/{'st' if r['ch']==2 else 'mo'}"
        edge = f"{r['edge'][0]:+.3f},{r['edge'][1]:+.3f}"
        st = f"{r['steady']:.2f}@{r['steady_hz']:.0f}" if r['steady'] else '0'
        status = 'OK' if not r['violations'] else 'FAIL: ' + ', '.join(r['violations'])
        print(f"{r['file']:42s} {fmt:>11s} {r['dur']:6.2f} {r['lufs']:6.1f} {r['tp']:6.2f} {r['lead']:5.3f} {r['trail']:5.3f} "
              f"{r['seam_pct']:6.1f} {edge:>13s} {st:>11s}  {status}")
        if r['tonal']: print(f"    info: long-term spectral peaks (Hz, dB above local median; pulsed/decaying accents expected, not a failure by itself): {r['tonal'][:8]}")
        if r['dips']: print(f"    level dips (t s, ms, dB): {r['dips']}")
        if r.get('corr') is not None: print(f"    stereo: L/R correlation {r['corr']:.2f}, mono fold-down {r['mono_delta']:+.1f} LU vs stereo")
    print(f"\n{sum(not r['violations'] for r in rows)}/{len(rows)} files pass.  "
          "seam% = percentile of the end->start jump among all sample-to-sample steps (loops only meaningful). "
          "steady = longest SUSTAINED narrow tone (s @ Hz; decaying bells stop counting after -6 dB), limit 0.3 s for sfx/jingles/ui/ambience; info only for music.")
    out = next((a for a in sys.argv[1:] if a.endswith('.json')), None)
    if out: json.dump(rows, open(out, 'w'), indent=1, default=float)
    sys.exit(1 if any(r['violations'] for r in rows) else 0)
