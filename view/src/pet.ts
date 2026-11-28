// The pet's genome (SPEC §11): numbers, which petsprite.ts turns into a sprite. The pet never draws.
export type Genome = {
  roundness: number; stretch: number; wobble: number; hue: number; saturation: number; pattern: string;
  pattern_density: number; eye_size: number; eye_spacing: number; limbs: number; marks: string[];
  // SPEC-v3.5 §2: its body plan and the part in each slot (view/assets/bodies.json); `size` 0.8 to 1.2. A genome from
  // before these has none of them: one blob, drawn as it always was (and its feet by `limbs`, which is otherwise retired).
  plan?: string; ears?: string; tail?: string; head?: string; whiskers?: string; feet?: string; mouth?: string; fur?: string; shade?: string; size?: number;
};

/** How it is just now, beyond its genome: half-shut eyes, an elder's greying (0 to 1), lying dead. Display only. */
export type Look = { tired?: boolean; grey?: number; dead?: boolean };

/** SPEC-v4.2 §11.3: how each stage of sickness (contracts.SICK) shows in the room. `pale`: its coat pale and greenish
 *  (petsprite's sick look); `bed`: it lies down whenever it is not walking, under a cloth; `down`: it does not get up. */
export type Decline = { pale: boolean; bed: boolean; down: boolean };
export const DECLINE: Record<string, Decline> = {
  "unwell": { pale: true, bed: false, down: false },
  "ill": { pale: true, bed: true, down: false },
  "gravely ill": { pale: true, bed: true, down: true },
};
/** Its decline as the room shows it (nothing while v4.2 is off): its sickness by DECLINE, and `stoop` for an elder in
 *  its last days, "old and slow". A poisonous catch it carries, or is about to eat, shows nothing: that is the point. */
export function declineOf(p: { stage: string; sick?: { level: string } | null; old?: boolean }, on: boolean): Decline & { stoop: boolean } {
  const none = { pale: false, bed: false, down: false, stoop: false };
  if (!on || p.stage === "egg" || p.stage === "dead") return none;
  return { ...none, ...DECLINE[p.sick?.level ?? ""], stoop: !!p.old && p.stage === "elder" };
}
