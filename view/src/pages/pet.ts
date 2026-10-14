// SPEC-v3.5.3: the pet page. main.ts calls render() on every visit to its address, and again every few seconds while it is shown.
export function render(root: HTMLElement, id: string | null): void {
  root.textContent = `pet ${id ?? ""}`;
}
