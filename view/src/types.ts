// What the engine sends (engine/server.py: snapshot, pet_view, room_view). The view only ever reads these.
import type { Invention } from "./parts";
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
  loud?: boolean; hums?: boolean;   // SPEC-v3.3 §4: it sounds when used; it is making a noise by itself right now
  star?: number | null;   // SPEC-v3.5.4 §10: the tick the visitor gave it a star
  // SPEC-v3.5.8 §6 (recorded from then on; an older thing has none): its maker's title shows (a first, an invention, an
  // heirloom, a statue, a gift, starred: `recipe.title`); how and where it was made, the bits it was made from, who used
  // it how often, and what a hob said or thought about it as it made it or set it down
  title_shown?: boolean; how?: string; made_in?: string; from?: string[]; users?: Record<string, number>;
  words?: { tick: number; pet: string; text: string; at: "made" | "set down" }[];
};
/** SPEC-v3.3 §2. A thing that keeps things: how many, which (by name), and whether they go in it (a chest) or on it (a shelf). */
export type Store = { cap: number | null; holds: string[]; inside: boolean; bits?: string[] };   // `bits`: the loose bits tidied into it, by name ("string", "bell")
/** SPEC-v3.3 §1, §5.4: what a pet's body is doing by itself between the things its mind decides. `icon` names the
 *  sprite icon.act.<icon>; `walking` is true while it is on its way to `goal`; `since` is the tick it set out. */
export type Body = { activity: string; doing: string; icon: string | null; what: string | null; who: string | null; since: number;
  passive: boolean; walking: boolean; goal: Tile | null; carrying?: boolean };   // `carrying`: the thing it names is in its paws, on the way to where it goes
/** SPEC-v3.3 §4: a small sound a pet made in its own voice, numbered so it is played once. */
export type Vox = { n: number; tick: number; pet: string; room: string; kind: "murmur" | "hum" | "chirp" | "yawn" | "laugh" | "greet" | "grumble" | "gasp" };
/** SPEC-v3.4 §2.1: something a pet wants, in its own packet's words ("you want to know what is behind the north door"). */
export type Want = { text: string; what: string; since: number };
/** SPEC-v3.4 §5: the moment a pet got what it wanted ("want") or found something out ("find"), numbered so it is shown once. */
export type Burst = { n: number; tick: number; pet: string; room: string; kind: "want" | "find"; text: string };
/** SPEC-v3.3 §3: the visitor's music (`scope` is "house" or a room id) and the radio control (`theirs`: the pets have
 *  found their own box, so the control switches that one; otherwise it is the visitor's "little radio"). */
export type Dj = { music: { mood: string; scope: string; since: number } | null; moods: string[];
  radio: { on: boolean; theirs: boolean; rooms: string[]; station: string; stations: Station[]; now: { title: string; at: number } | null } };
/** SPEC-v3.5.1 §5: a real internet station the radio can play (`stream` is what the page plays; `home` its own page). */
export type Station = { id: string; name: string; mood: string; sound: string; stream: string; home: string };
/** SPEC-v3.5.1 §2: what the lit sign in the hub runs (the time it takes from the clock). */
export type Ticker = { room: string | null; forecast: { text: string; anim: string }; cold: boolean; headlines: { n: number; tick: number; kind: string; text: string; anim: string | null }[];
  board?: BoardLine[] };   // SPEC-v3.5.4 §11
/** A line of the board: "WHAT: WHO" in its capitals; the Works' has its meter ([have, need]) and its fullness in words. */
export type BoardLine = { key: string; text: string; kind: string; pets: string[]; meter: [number, number] | null; says?: string; what?: string };
export type Obj = {
  pos: Tile; state?: string | null; made?: Made; memorial?: { pet: string; text: string }; wall?: boolean; says?: string;   // wall: it hangs on the north wall above `pos`
  words?: { tick: number; pet: string; text: string }[];   // SPEC-v3.5.8 §6: words written on a stone
  fix?: Record<string, unknown>; water?: Tile[]; grow?: number; servings?: number;
  // SPEC-v3.3 §2: `on`: it is put away on (or in) the thing of that name and stands on that thing's tile; `store`: it
  // keeps things; `home`: where it belongs
  on?: string; store?: Store; home?: { room: string; on?: string; pos?: Tile };
  // SPEC-v3.4 §3.5: something is planted in it (a pot, a planting bed): what, how far it has grown, and whether it has wilted
  planted?: { what: string; stage: "planted" | "sprout" | "leaves" | "ripe"; wilted: boolean };
  // SPEC-v3.5 §4.1: it is being built, or was built by the pets: the picture to draw it with, what to call it ("the bench
  // Lean built"), and, under way, how far along it is (0 to 1); `flat`: it lies on the floor; `glow`: a soft light at night
  build?: { sprite: string; title: string; progress?: number; flat?: boolean; glow?: boolean; worn?: boolean };
  // SPEC-v3.5.1 §3, §4: what is on a screen's glass (who asked what, and what it read); a statue of a family's founder
  screen?: { pet: string; by?: string; asked: string; title: string | null; text: string | null; tick: number };
  statue?: { of: string; family: number; genome: Genome | null; stage: string; name: string | null; words: string | null };
};
/** SPEC-v3.5 §4.2: one painted place in a room: a stretch of the north wall or a patch of floor (`at`: its first tile; three
 *  tiles wide, a floor patch two deep) or a rug (`at`: its name), in the dye's `color` with `pattern` (stripes, dots, border)
 *  through it in the painter's coat colour (`hue`); `strength` 1 new to 0 faded away. */
export type Painted = { where: "wall" | "floor" | "rug"; at: Tile | string; color: string; hue: number; pattern: string; by: string; name: string; family: number; tick: number; strength?: number };
/** An inscription (SPEC-v3.1 §2): `on` is a wall or the name of a thing, `at` how far along the wall, `clarity` 1 new to 0 gone. */
export type Mark = { id: number; text: string; by: string; by_name?: string; family?: number; on: string; medium: string; tick: number; fresh?: number; at?: number; clarity?: number };
export type Note = [string, number];   // a pitch of the five-note scale ("low do" … "high la"), and whether it is held long
export type Song = { id: string; name: string; notes: Note[]; by: string; from?: string | null; how?: string; tick: number; family?: number };
export type Sung = { tick: number; by: string; song: string; room: string };
export type Heard = { tick: number; room: string | null; source: string; text: string };   // what the box said; "" is static
/** A bit to gather (SPEC-v3.4 §5). `loose` false: the room grows it here, on its source, and `ready` says whether it is
 *  there just now or still growing back. `loose` true (or not said: an older recording): a pet dropped it. `on`: put away in that. */
export type BitSpot = { bit: string; pos: Tile; ready?: boolean; loose?: boolean; on?: string };
export type RoomV = {
  id: string; cell: Tile; type: string | null; doors: Record<string, string>; marks?: Mark[];
  name: string; paint: { wall: string | null; floor: string | null }; shut: string[]; wet: boolean; cold: boolean; lit: boolean;
  sounding: boolean; found: number; by: string | null; objects: Record<string, Obj>; spots: BitSpot[];
  // SPEC-v3.3 §2: how much lies about (0 tidy, 1 a few things, 2 a mess) in the pets' own words, and the places the
  // room has grown ("sleeping corner", "making bench", "keepsake shelf"): a faint tint and a line in hover cards
  mess?: 0 | 1 | 2; mess_says?: string; areas?: { name: string; tiles: Tile[]; on?: string }[];
  painted?: Painted[];   // SPEC-v3.5 §4.2
};
/** `idle` (SPEC-v3.3): every step it decided is done (or it decided none); the thought stays with it and its body carries on. */
export type Plan = { intention: string; thought: string; expect: string; i: number; why: string; steps: string[]; acting: boolean; idle?: boolean };
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
  ambition?: string | null;   // SPEC-v3.5.4 §9: what it means to do with its life
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
  // SPEC-v3.3; absent in older recordings. `body`: what it is doing by itself (null while it carries out a step it
  // decided, and while asleep). `focus`: what its mind wants to be about. `habits`: up to three, in plain words.
  // `react`: it was last stopped in its tracks at this tick ("startle" at an event, "turn" when spoken to).
  body?: Body | null; focus?: { type: string; words: string; says?: string; who: string | null; what: string | null; since: number } | null;
  // `focus.says`: the focus in plain words ("wants to be with Quiet"). `sign`: while it carries out a step it decided,
  // the icon for it (sprite icon.act.<icon>) and what it is doing in words.
  sign?: { icon: string | null; word: string; step: string; walking: boolean } | null;
  habits?: string[]; react?: { tick: number; kind: "startle" | "turn" } | null; orderly?: number;
  // SPEC-v3.4 §2, §3.3; absent in older recordings. `wants`: up to three. `skills`: how practised it
  // is, in its own words ("your paws are surer at the bench"; may be ""). `recipes`: what it has found out.
  wants?: Want[]; skills?: string; recipes?: string[];
  mutation?: { slot: string; from: string; to: string } | null;   // SPEC-v3.5 §2.2: born with something no ancestor had
  // SPEC-v3.5.8 §6: what its family calls it ("Open Hand"), shown under its name; a project's measurable progress
  byname?: string | null; progress?: { what: string; have: number; need: number } | null;
  riding?: string | null;   // SPEC-v3.5.12 §3: the train it rides in
};
/** `tame` is the pet it belongs to. (The engine also sends its trust in each pet; that is hidden and never shown.) */
/** A step a pet has just finished (SPEC-v3.2 §5.2). `what` is the thing, bit or song it was about, `to` whom or
 *  where; `kind`/`color` describe a thing that was made, unmade or combined; `ok` false means it turned out not possible. */
export type Act = { n: number; tick: number; pet: string; type: string; what?: string | null; to?: string | null; room: string; ok: boolean;
  kind?: string | null; color?: string | null; from?: string[] | null; to_id?: string | null; text?: string | null;
  body?: string; loud?: boolean };   // SPEC-v3.3: `body`: its body did it unasked (the activity's name); `loud`: the thing sounds
export type Creature = { id: string; kind: string; room: string; pos: Tile; doing: string; carry: string | null; tame?: string | null; name?: string | null;
  load?: number; full?: boolean; docked?: boolean;   // SPEC-v3.5.8 §4.2: the sweeper's: how much it has picked up, full (its light blinks), on its dock
  // SPEC-v3.5.12 §3: the train's (kind "train"): its three cars, engine, cart, tram (null: not through a door yet); the
  // tiles its leading car last passed, newest first; which end leads; its bell (the tick it last rang); who rides; what is in the cart
  cars?: (Car | null)[]; trail?: [string, Tile][]; lead?: "engine" | "tram"; moving?: boolean; lid?: "open" | "closed"; bell?: number;
  asleep?: boolean; rider?: string | null; cargo?: string[]; speed?: number };
export type Car = { room: string; pos: Tile; dir: string };
/** SPEC-v3.5.12 §3: the rail, once the Works has built it. Each room's track is branches of tiles, each from a door tile
 *  to the platform; `side`: the tile beside the platform for its bench or post; `due`: the tick the train next stops here (null: in the morning). */
export type RailRoom = { track: Tile[][]; platform: Tile; side: Tile; buffer: boolean; due: number | null };
export type Rail = { built: number; depot: string; route: string[]; rooms: Record<string, RailRoom> };
export type Moment = { n: number; tick: number; day: number; hour: number; kind: string; text: string; pet: string | null; room: string | null };
export type HouseEvent = { tick: number; day: number; kind: string; room: string | null; detail: string };
export type Chronicle = { day: number; season: string; summary: string; lines: string[]; text: string | null };
export type Lineage = { id: number; started: number; ended: number | null; founder: string };
export type Hello = {
  bits: Record<string, { can: string[]; looks: { shape: string; color: string } }>;
  properties: Record<string, string>; rooms: Record<string, { name: string; feel: string }>;
};
export type Snap = {
  tick: number; clock: Clock; weather: string; power: boolean; size: [number, number]; tick_seconds: number; day_seconds: number; shift?: { until: number; by: number } | null;
  turbo: boolean; profile: string | null; start: string; door_tiles: Record<string, Tile>; lineage: Lineage;
  rooms: RoomV[]; pets: PetV[]; creatures: Creature[]; moments: Moment[]; events: HouseEvent[]; chronicle: Chronicle[];
  visitor: string | null; population: number; sayings: { text: string; gens: number; truth: string | null }[];
  // SPEC-v3.2: the one plain sentence about the house right now, and the steps finished in the last few world seconds
  // (each with a running number `n`, so an animation plays once)
  now?: string; acts?: Act[];
  // SPEC-v3.1
  arrived?: Record<string, number>; pace?: number; songs?: Record<string, Song>; sung?: Sung[]; read_glow?: boolean;
  radio?: { here: boolean; on: boolean; said: Heard[] };
  // SPEC-v3.3: the visitor's music and radio, the small sounds pets make, and every body activity with its icon
  dj?: Dj; vox?: Vox[]; activities?: Record<string, { icon: string | null; passive: boolean; rest: boolean }>;
  bursts?: Burst[];   // SPEC-v3.4 §5
  machine?: { stock: Record<string, number>; limit: number; materials: string[]; room: string } | null;   // SPEC-v3.5 §4.3: what the vending machine holds (null: nobody has found it)
  invented?: Record<string, Invention>;   // SPEC-v3.5 §3: the kinds this house invented, by name: drawn from their parts
  ticker?: Ticker;   // SPEC-v3.5.1 §2
  rail?: Rail | null;   // SPEC-v3.5.12 §3
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
