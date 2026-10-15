// SPEC-v3.5.6 §6, §9: a name shown only on hover (a mouse) or on a tap (a finger), on a paper strip (skin.css .paper:
// Travel Book Popup01a, the same as the room's #tip). One box for the page. tipOn() gives a link one: with a mouse it
// shows while the pointer is on the link and the click opens it; with a finger the first tap shows it and a second tap
// (on the link, or a link inside the tip) opens it; from the keyboard it shows on focus and Enter opens it.
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

/** Give `link` its tip, made by `kids` when it is shown. */
export function tipOn(link: HTMLAnchorElement, kids: () => Node[]) {
  let finger = false;
  link.addEventListener("pointerdown", (e) => (finger = e.pointerType !== "mouse"));
  link.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") showTip(link, kids()); });
  link.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse" && on === link) hideTip(); });
  link.addEventListener("focus", () => { if (!finger) showTip(link, kids()); });
  link.addEventListener("blur", () => { if (on === link && !finger) hideTip(); });
  link.addEventListener("click", (e) => {
    if (finger && on !== link) { e.preventDefault(); showTip(link, kids(), true); }
    finger = false;
  });
}

// anything else touched, the page scrolled, or another page opened: the tip goes
addEventListener("pointerdown", (e) => { if (on && !box.contains(e.target as Node) && !on.contains(e.target as Node)) hideTip(); }, true);
addEventListener("scroll", () => { if (on) hideTip(); }, true);
addEventListener("hashchange", hideTip);
