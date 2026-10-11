// What the engine sends (engine/server.py: snapshot, pet_view, room_view). The view only ever reads these.
import type { Genome } from "./pet";
import type { Part, Recipe } from "./things";

export type Need = "energy" | "comfort" | "curiosity" | "company";
export const NEEDS: Need[] = ["energy", "comfort", "curiosity", "company"];
export type Tile = [number, number];
export type Clock = { hour: number; day: number; phase: "day" | "dusk" | "night"; season: string; morning: boolean; year: number };
export type Heirloom = { from: string; to: string[]; tick: number; line: string[] };
export type Made = {
  id: string; recipe: Recipe; owner: string; owner_name: string | null; by: string; heirloom: Heirloom | null;
  behavior: { when: string; do: string } | null; active: boolean; uses: number; ups: number; useful: boolean;
  called: string | null; tick: number; worn: string[];
};
export type Obj = {
  pos: Tile; state?: string | null; made?: Made; memorial?: { pet: string; text: string }; wall?: boolean; says?: string;   // wall: it hangs on the north wall above `pos`
  fix?: Record<string, unknown>; water?: Tile[]; grow?: number; servings?: number;
};
/** An inscription (SPEC-v3.1 §2): `on` is a wall or the name of a thing, `at` how far along the wall, `clarity` 1 new to 0 gone. */
export type Mark = { id: number; text: string; by: string; by_name?: string; family?: number; on: string; medium: string; tick: number; fresh?: number; at?: number; clarity?: number };
export type Note = [string, number];   // a pitch of the five-note scale ("low do" … "high la"), and whether it is held long
export type Song = { id: string; name: string; notes: Note[]; by: string; from?: string | null; how?: string; tick: number; family?: number };
export type Sung = { tick: number; by: string; song: string; room: string };
export type Heard = { tick: number; room: string | null; source: string; text: string };   // what the box said; "" is static
export type RoomV = {
  id: string; cell: Tile; type: string | null; doors: Record<string, string>; marks?: Mark[];
  name: string; paint: { wall: string | null; floor: string | null }; shut: string[]; wet: boolean; cold: boolean; lit: boolean;
  sounding: boolean; found: number; by: string | null; objects: Record<string, Obj>; spots: { bit: string; pos: Tile }[];
};
export type Plan = { intention: string; thought: string; expect: string; i: number; why: string; steps: string[]; acting: boolean };
export type PetV = {
  id: string; name: string | null; label: string; stage: string; room: string; pos: Tile; gen: number; parent: string | null;
  children: string[]; word: string; genome: Genome; temper: Record<string, number>; eggs: number; laid: number; born: number | null;
  died: number | null; cause: string | null; lineage: number; buried: boolean; made: number; useful: number; stage_before?: string | null;
  days?: number | null; fade?: number; hatches_in?: number;
  // living and hatched only
  needs?: Record<Need, number>; levels?: Record<Need, number>; feelings?: string; felt?: Record<Need, string>; seems?: string; doing?: string; asleep?: boolean;
  thinking?: string | null; carrying?: string[]; following?: string | null; weak?: boolean;
  said?: { text: string; tick: number; to: string | null; to_name: string | null; song?: string } | null;
  project?: { text: string; since: number } | null; plan?: Plan | null; step?: string | null;
  last_plan?: { intention: string; ended: string; score: string } | null; calls_hour?: number; spring?: boolean;
  portrait?: { day: number; parts: Part[] } | null; old?: boolean;
  // the visitor's naming: the name offered, whether the pet has taken it, and the tick it did
  naming?: { offered: string; took: boolean; at: number | null } | null;
  // SPEC-v3.2; absent in older recordings. `mood`: at most two plain words, worst first. `emote`: one strong feeling,
  // or null. `act`: the step it is on now (walking to it, or doing it once plan.acting is true).
  stage_word?: string; mood?: string[]; emote?: "tired" | "uneasy" | "lonely" | "bored" | "content" | null;
  act?: { type: string; what?: string | null; to?: string | null; since: number } | null;
  // SPEC-v3.1; a recording made before it has none of these
  family?: number; songs?: string[]; animals?: { id: string; kind: string; name: string | null; room: string }[];
  read?: { tick: number; question: string; title: string; text: string }[];
};
/** `tame` is the pet it belongs to. (The engine also sends its trust in each pet; that is hidden and never shown.) */
/** A step a pet has just finished (SPEC-v3.2 §5.2). `what` is the thing, bit or song it was about, `to` whom or
 *  where; `kind`/`color` describe a thing that was made, unmade or combined; `ok` false means it turned out not possible. */
export type Act = { n: number; tick: number; pet: string; type: string; what?: string | null; to?: string | null; room: string; ok: boolean;
  kind?: string | null; color?: string | null; from?: string[] | null; to_id?: string | null; text?: string | null };
export type Creature = { id: string; kind: string; room: string; pos: Tile; doing: string; carry: string | null; tame?: string | null; name?: string | null };
export type Moment = { n: number; tick: number; day: number; hour: number; kind: string; text: string; pet: string | null; room: string | null };
export type HouseEvent = { tick: number; day: number; kind: string; room: string | null; detail: string };
export type Chronicle = { day: number; season: string; summary: string; lines: string[]; text: string | null };
export type Lineage = { id: number; started: number; ended: number | null; founder: string };
export type Hello = {
  bits: Record<string, { can: string[]; looks: { shape: string; color: string } }>;
  properties: Record<string, string>; rooms: Record<string, { name: string; feel: string }>;
};
export type Snap = {
  tick: number; clock: Clock; weather: string; power: boolean; size: [number, number]; tick_seconds: number; day_seconds: number;
  turbo: boolean; profile: string | null; start: string; door_tiles: Record<string, Tile>; lineage: Lineage;
  rooms: RoomV[]; pets: PetV[]; creatures: Creature[]; moments: Moment[]; events: HouseEvent[]; chronicle: Chronicle[];
  visitor: string | null; population: number; sayings: { text: string; gens: number; truth: string | null }[];
  // SPEC-v3.2: the one plain sentence about the house right now, and the steps finished in the last few world seconds
  // (each with a running number `n`, so an animation plays once)
  now?: string; acts?: Act[];
  // SPEC-v3.1
  arrived?: Record<string, number>; pace?: number; songs?: Record<string, Song>; sung?: Sung[]; read_glow?: boolean;
  radio?: { here: boolean; on: boolean; said: Heard[] };
  hello?: Hello; error?: string;
};
/** What /api/v31 answers: everything ever written, sung, asked and heard, and when each discovery comes. */
export type V31 = {
  walls?: (Mark & { room: string; room_name: string; place: string; fate: string; gone?: number; gone_by?: string | null })[];
  songs?: (Song & { by_name: string; parent: string | null; known_by: string[]; sounds: string })[];
  library?: { pet: string; name: string; tick: number; question: string; title: string; text: string }[];
  radio?: Heard[]; crossed?: { text: string; families: number[] }[]; ticks_per_day?: number;
  arrivals?: Record<string, { arrived: number | null; due: number }>;
};

/** Real milliseconds a tick of the house takes: the live clock runs slower than the world's (`pace`). */
export const tickMs = (s: { tick_seconds: number; pace?: number }) => s.tick_seconds * (s.pace ?? 1) * 1000;
/** Real seconds since a tick: how long ago something happened, for whoever is watching. */
export const ago = (s: { tick: number; tick_seconds: number; pace?: number }, tick: number) => ((s.tick - tick) * tickMs(s)) / 1000;
/** A family's colour (§7.4) as a class for the page; anything that is nobody's family gets none. */
export const fam = (n: number | undefined) => (n === 2 ? "fam2" : n === 1 || n == null ? "fam1" : "");
export const hhmm = (hour: number, m = Math.round(hour * 60)) => `${Math.floor(m / 60) % 24}:${String(m % 60).padStart(2, "0")}`;   // to the minute: 2.4 hours is 2:24, not 2:23
/** The stage a body is drawn at: a dead pet keeps the body it died in. */
export const bodyStage = (p: { stage: string; stage_before?: string | null }) => (p.stage === "dead" ? p.stage_before ?? "adult" : p.stage);
