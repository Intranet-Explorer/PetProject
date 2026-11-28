// SPEC-v3.5.6 §6, §9: a name shown on hover, on a paper strip (skin.css .paper: Travel Book Popup01a, the same as the
// room's #tip). One box for the page. (SPEC-v3.5.7 §7: the Things tab's slots show it under a mouse; a tap chooses.)
import { el } from "../dom";

const box = el("div", "tipbox paper ptip");
box.hidden = true;
box.setAttribute("role", "tooltip");
let on: HTMLElement | null = null;

export function hideTip() {
  box.hidden = true;
  on = null;
}

/** Show `kids` in the tip beside `at`: over it if there is room, else under it, kept inside the window. `touch`: it
 *  takes taps (a link in it can be followed). */
export function showTip(at: HTMLElement, kids: Node[], touch = false) {
  if (!box.isConnected) document.body.append(box);
  box.replaceChildren(...kids);
  box.style.pointerEvents = touch ? "auto" : "";
  box.hidden = false;
  on = at;
  const r = at.getBoundingClientRect(), w = box.offsetWidth, h = box.offsetHeight, gap = 4;
  const y = r.top - h - gap >= 8 ? r.top - h - gap : Math.min(r.bottom + gap, innerHeight - h - 8);
  box.style.left = `${Math.round(Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)))}px`;
  box.style.top = `${Math.round(Math.max(8, y))}px`;
}

// anything else touched, the page scrolled, or another page opened: the tip goes
addEventListener("pointerdown", (e) => { if (on && !box.contains(e.target as Node) && !on.contains(e.target as Node)) hideTip(); }, true);
addEventListener("scroll", () => { if (on) hideTip(); }, true);
addEventListener("hashchange", hideTip);
