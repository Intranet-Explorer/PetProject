// SPEC-v3.5.7 §9: the page's own small sounds, made in the browser: a soft click for buttons, a page flip, a chime for
// firsts and builds (a softer one for a birth), a low tone for a death. They follow the Sound switch: nothing plays
// while it is off. Anything may ask for one with `window.dispatchEvent(new CustomEvent("pet:sound", {detail: kind}))`.
let ctx: AudioContext | null = null;
let on = () => false;
let volume = () => 0.8;

export function initUiSound(isOn: () => boolean, vol: () => number) {
  on = isOn;
  volume = vol;
  addEventListener("pet:sound", (e) => play((e as CustomEvent<string>).detail));
}

function tone(c: AudioContext, at: number, f: number, len: number, peak: number, type: OscillatorType = "sine", to = f) {
  const o = c.createOscillator(), g = c.createGain();
  o.type = type;
  o.frequency.setValueAtTime(f, at);
  if (to !== f) o.frequency.exponentialRampToValueAtTime(to, at + len);
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(peak * volume(), at + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, at + len);
  o.connect(g).connect(c.destination);
  o.start(at);
  o.stop(at + len + 0.02);
}

export function play(kind: string) {
  if (!on()) return;
  try {
    ctx ??= new AudioContext();
    if (ctx.state === "suspended") void ctx.resume();
    const c = ctx, t = c.currentTime + 0.01;
    if (kind === "click") tone(c, t, 1400, 0.03, 0.04, "square", 900);
    else if (kind === "flip") {   // a short brush of noise, falling
      const n = c.createBuffer(1, Math.round(c.sampleRate * 0.16), c.sampleRate), d = n.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length) ** 2;
      const src = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
      f.type = "bandpass";
      f.frequency.setValueAtTime(2400, t);
      f.frequency.exponentialRampToValueAtTime(700, t + 0.16);
      g.gain.value = 0.12 * volume();
      src.buffer = n;
      src.connect(f).connect(g).connect(c.destination);
      src.start(t);
    } else if (kind === "chime") { tone(c, t, 880, 0.35, 0.08); tone(c, t + 0.09, 1318.5, 0.5, 0.07); }
    else if (kind === "soft") { tone(c, t, 660, 0.6, 0.05, "sine", 880); }
    else if (kind === "low") { tone(c, t, 110, 0.9, 0.06, "sine", 98); }
  } catch { /* no sound here */ }
}
