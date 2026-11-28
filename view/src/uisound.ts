// SPEC-v3.5.7 §9, AUDIO-BRIEF batch 7: the page's own small sounds, from view/assets/audio/ui (sounds.json `ui.*`): a
// very quiet click and hover for buttons, a tab, a card or a box opening, a switch, a slider, the "while you were away"
// digest, something gone wrong; a page turned; the tram's bell. They follow the Sound switch: nothing plays while it is
// off. Anything may ask for one with `window.dispatchEvent(new CustomEvent("pet:sound", {detail: kind}))`.
let play: (kind: string) => unknown = () => {};

export function initUiSound(ui: (kind: string) => unknown) {
  play = ui;
  addEventListener("pet:sound", (e) => play((e as CustomEvent<string>).detail));
  // every button and link of the page, from one listener: what kind of control it is says which sound
  document.addEventListener("click", (e) => {
    const t = (e.target as HTMLElement | null)?.closest("button, a, summary, [role=tab]") as HTMLElement | null;
    if (!t || (t as HTMLButtonElement).disabled) return;
    play(t.getAttribute("role") === "tab" || t.classList.contains("tab") ? "tab" : t.hasAttribute("popovertarget") || t.tagName === "SUMMARY" ? "open" : t.hasAttribute("aria-pressed") ? "toggle" : "click");
  }, { capture: true });
  document.addEventListener("pointerover", (e) => { if ((e.target as HTMLElement | null)?.closest?.("button:not(:disabled)") && (e as PointerEvent).pointerType === "mouse") play("hover"); });
  document.addEventListener("change", (e) => { if ((e.target as HTMLInputElement | null)?.type === "range") play("slider"); });
  document.addEventListener("toggle", (e) => { const t = e.target as HTMLElement; if (t.hasAttribute?.("popover") && (e as ToggleEvent).newState === "closed") play("close"); }, { capture: true });
}
