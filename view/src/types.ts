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
  pos: Tile; state?: string | null; made?: Made; memorial?: { pet: string; text: string };
  fix?: Record<string, unknown>; water?: Tile[]; grow?: number; servings?: number;
};
export type RoomV = {
  id: string; cell: Tile; type: string | null; doors: Record<string, string>;
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
  said?: { text: string; tick: number; to: string | null; to_name: string | null } | null;
  project?: { text: string; since: number } | null; plan?: Plan | null; step?: string | null;
  last_plan?: { intention: string; ended: string; score: string } | null; calls_hour?: number; spring?: boolean;
  portrait?: { day: number; parts: Part[] } | null; old?: boolean;
};
export type Creature = { id: string; kind: string; room: string; pos: Tile; doing: string; carry: string | null };
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
  hello?: Hello; error?: string;
};

export const hhmm = (hour: number) => `${Math.floor(hour)}:${String(Math.floor((hour % 1) * 60)).padStart(2, "0")}`;
/** The stage a body is drawn at: a dead pet keeps the body it died in. */
export const bodyStage = (p: { stage: string; stage_before?: string | null }) => (p.stage === "dead" ? p.stage_before ?? "adult" : p.stage);
