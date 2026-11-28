// The room's lettering: a 5 x 7 pixel face (tails hang two rows lower), drawn in whole pixels like everything else in the room. Used for name
// plates, thought captions, speech and the writing on the walls. (Letters are code, not an asset: the classic 5 x 7
// column font, one byte a column, lowest bit at the top; each glyph is trimmed to its own width.)
import { seeded } from "./geom";

const COLS = "0000000000 00005F0000 0007000700 147F147F14 242A7F2A12 2313086462 3649552250 0005030000 001C224100 0041221C00 14083E0814 08083E0808 0050300000 0808080808 0060600000 2010080402 " +
  "3E5149453E 00427F4000 4261514946 2141454B31 1814127F10 2745454539 3C4A494930 0171090503 3649494936 064949291E 0036360000 0056360000 0814224100 1414141414 0041221408 0201510906 " +
  "324979413E 7E1111117E 7F49494936 3E41414122 7F4141221C 7F49494941 7F09090901 3E4149497A 7F0808087F 00417F4100 2040413F01 7F08142241 7F40404040 7F020C027F 7F0408107F 3E4141413E " +
  "7F09090906 3E4151215E 7F09192946 4649494931 01017F0101 3F4040403F 1F2040201F 3F4038403F 6314081463 0708700807 6151494543 007F414100 0204081020 0041417F00 0402010204 4040404040 " +
  "0001020400 2054545478 7F48444438 3844444420 384444487F 3854545418 087E090102 0C5252523E 7F08040478 00447D4000 2040443D00 7F10284400 00417F4000 7C04180478 7C08040478 3844444438 " +
  "7C14141408 081414187C 7C08040408 4854545420 043F444020 3C4040207C 1C2040201C 3C4030403C 4428102844 0C5050503C 4464544C44 0008364100 00007F0000 0041360800 0804081008";
/** Each glyph as its columns (bits 0..6, top to bottom). */
const GLYPHS = new Map<string, number[]>();
COLS.split(" ").forEach((hex, n) => {
  let cols = [0, 2, 4, 6, 8].map((i) => parseInt(hex.slice(i, i + 2), 16));
  while (cols.length && !cols[0]) cols = cols.slice(1);
  while (cols.length && !cols[cols.length - 1]) cols.pop();
  GLYPHS.set(String.fromCharCode(32 + n), cols.length ? cols : [0, 0]);
});
// letters with a tail get a real one, two rows below the line (in seven rows a "g" reads as a "9")
GLYPHS.set("g", [0x38, 0x144, 0x144, 0x144, 0xfc]);
GLYPHS.set("y", [0x3c, 0x140, 0x140, 0x140, 0xfc]);
GLYPHS.set("p", [0x1fc, 0x44, 0x44, 0x44, 0x38]);
GLYPHS.set("q", [0x38, 0x44, 0x44, 0x44, 0x1fc]);
GLYPHS.set("j", [0x100, 0x104, 0xfd]);
GLYPHS.set("…", [0x40, 0, 0x40, 0, 0x40]);
GLYPHS.set("×", [0x44, 0x28, 0x10, 0x28, 0x44]);
GLYPHS.set("→", [0x08, 0x08, 0x2a, 0x1c, 0x08]);
GLYPHS.set("♪", [0x30, 0x38, 0x1f, 0x02, 0x04]);
GLYPHS.set("·", [0x18, 0x18]);
const SWAP: Record<string, string> = { "‘": "'", "’": "'", "“": '"', "”": '"', "—": "-", "–": "-", " ": " ", "\t": " ", "\n": " " };

export const LINE = 10;   // the height of a line: seven rows, two below for tails, one of air
const ROWS = 9;
/** Text as this face can draw it: accents dropped, curly quotes straightened, anything unknown a "?". */
export function plain(text: string) {
  let out = "";
  for (const ch of text.normalize("NFD").replace(/[̀-ͯ]/g, "")) {
    const c = SWAP[ch] ?? ch;
    out += GLYPHS.has(c) ? c : "?";
  }
  return out;
}
export function measure(text: string) {
  let w = 0;
  for (const ch of text) w += (GLYPHS.get(ch)?.length ?? 3) + 1;
  return Math.max(0, w - 1);
}

/** Break into at most `lines` lines no wider than `max`; what does not fit ends in "…". */
export function wrap(text: string, max: number, lines = 2): string[] {
  const words = plain(text).trim().split(/\s+/).filter(Boolean), out: string[] = [];
  let line = "", cut = false;
  for (let w of words) {
    if (out.length === lines) { cut = true; break; }
    const next = line ? `${line} ${w}` : w;
    if (measure(next) <= max) { line = next; continue; }
    if (line) { out.push(line); line = ""; }
    if (out.length === lines) { cut = true; break; }
    while (measure(w) > max && out.length < lines) {   // a word wider than a whole line is cut where it must be
      let n = w.length - 1;
      while (n > 1 && measure(w.slice(0, n)) > max) n--;
      out.push(w.slice(0, n));
      w = w.slice(n);
    }
    if (out.length === lines) { cut = true; break; }
    line = w;
  }
  if (line) out.push(line);
  if (cut && out.length) {
    let last = out[out.length - 1];
    while (last.length > 1 && measure(last + "…") > max) last = last.slice(0, -1);
    out[out.length - 1] = last.replace(/[\s,.;:]+$/, "") + "…";
  }
  return out;
}

export type Ink = { color: string; halo?: string; chalk?: string; alpha?: number };

/** Draw lines of text onto a canvas context at (x, y), one canvas pixel per font pixel. `chalk`: a key; some pixels
 *  are left out and the line wavers, like a hand on a wall. `halo`: a colour laid one pixel round every letter. */
export function draw(ctx: CanvasRenderingContext2D, lines: string[], x: number, y: number, ink: Ink) {
  const rnd = ink.chalk != null ? seeded(ink.chalk) : null;
  const pass = (color: string, grow: boolean) => {
    ctx.fillStyle = color;
    lines.forEach((text, n) => {
      let cx = x, dy = 0;
      const r = ink.chalk != null ? seeded(ink.chalk + n) : null;
      for (const ch of text) {
        if (r && ch === " ") dy = Math.round(r() * 1.6 - 0.8);   // a hand does not keep a level line: each word sits a little off
        const cols = GLYPHS.get(ch) ?? [0, 0, 0];
        cols.forEach((bits, i) => {
          for (let row = 0; row < ROWS; row++) if (bits & (1 << row)) {
            if (grow) ctx.fillRect(cx + i - 1, y + n * LINE + row + dy - 1, 3, 3);
            else if (!rnd || rnd() > 0.06) ctx.fillRect(cx + i, y + n * LINE + row + dy, 1, 1);
          }
        });
        cx += cols.length + 1;
      }
    });
  };
  ctx.globalAlpha = ink.alpha ?? 1;
  if (ink.halo) pass(ink.halo, true);
  pass(ink.color, false);
  ctx.globalAlpha = 1;
}

/** Lines of text as a canvas of their own, one canvas pixel per font pixel. */
export function textCanvas(lines: string[], ink: Ink) {
  const pad = ink.halo ? 1 : 0, c = document.createElement("canvas");
  c.width = Math.max(1, ...lines.map(measure)) + 2 * pad;
  c.height = (lines.length - 1) * LINE + ROWS + 2 * pad + (ink.chalk != null ? 1 : 0);
  draw(c.getContext("2d")!, lines, pad, pad, ink);
  return c;
}
